//! Path-only reservation for the fixed local inference namespaces.
//!
//! This is a check at an I/O boundary, not an OS sandbox or a race-free file
//! handle. It grants no access and does not protect against unchecked commands,
//! ancestor deletion/rename, hard links, or concurrent filesystem replacement.

use std::io;
use std::path::{Component, Path, PathBuf};

/// Resolve the closest existing ancestor, including for a not-yet-created file.
pub(crate) fn resolve_path(path: &Path) -> io::Result<PathBuf> {
    resolve_path_inner(path, 40)
}

fn resolve_path_inner(path: &Path, links_left: usize) -> io::Result<PathBuf> {
    let mut ancestor = path;
    let mut missing = Vec::new();
    loop {
        match std::fs::symlink_metadata(ancestor) {
            Ok(metadata) => {
                let mut resolved = match std::fs::canonicalize(ancestor) {
                    Ok(path) => path,
                    Err(error)
                        if error.kind() == io::ErrorKind::NotFound
                            && metadata.is_symlink()
                            && links_left > 0 =>
                    {
                        // A dangling link is still a known spelling of a future
                        // target. Resolve its existing ancestors instead of
                        // confusing missing runtime resources with a global I/O
                        // authorization failure.
                        let target = std::fs::read_link(ancestor)?;
                        let target = if target.is_absolute() {
                            target
                        } else {
                            ancestor
                                .parent()
                                .ok_or_else(|| io::Error::other("link has no parent"))?
                                .join(target)
                        };
                        resolve_path_inner(&target, links_left - 1)?
                    }
                    Err(error) => return Err(error),
                };
                for name in missing.iter().rev() {
                    resolved.push(name);
                }
                return Ok(resolved);
            }
            Err(error) if error.kind() == io::ErrorKind::NotFound => {
                let Some(name) = ancestor.file_name() else {
                    return Err(error);
                };
                missing.push(name.to_os_string());
                let Some(parent) = ancestor.parent() else {
                    return Err(error);
                };
                ancestor = parent;
            }
            Err(error) => return Err(error),
        }
    }
}

fn absolute_path(path: &Path) -> io::Result<PathBuf> {
    if !path.is_absolute() || path.components().any(|c| matches!(c, Component::ParentDir)) {
        return Err(io::Error::new(
            io::ErrorKind::PermissionDenied,
            "invalid absolute path",
        ));
    }
    Ok(path.components().collect())
}

#[derive(Clone, Debug)]
pub(crate) struct ReservedPaths {
    roots: Vec<PathBuf>,
}

impl ReservedPaths {
    /// Keep both spellings: a reserved symlink pointing out must not turn the
    /// reserved name into an allowed name, and aliases pointing in must fail.
    pub(crate) fn new(roots: impl IntoIterator<Item = PathBuf>) -> io::Result<Self> {
        let mut paths = Vec::new();
        for root in roots {
            let root = absolute_path(&root)?;
            paths.push(root.clone());
            match resolve_path(&root) {
                Ok(resolved) => paths.push(resolved),
                Err(_) => {
                    // A failed resource root is not a failed book operation.
                    // Keep its spelling denied and conservatively fence only
                    // the unresolved branch. This is NOT a resource-integrity
                    // or availability check: native execution must separately
                    // reject missing, unreadable or invalid fixed resources.
                    for ancestor in root.ancestors().skip(1) {
                        if let Ok(resolved) = resolve_path(ancestor) {
                            // Fence the first unresolved child, not the entire
                            // resolved ancestor: a broken private-root link must
                            // not reserve its sibling user library as well.
                            let child = root
                                .strip_prefix(ancestor)
                                .ok()
                                .and_then(|suffix| suffix.components().next())
                                .ok_or_else(|| io::Error::other("missing unresolved branch"))?;
                            paths.push(ancestor.join(child.as_os_str()));
                            paths.push(resolved.join(child.as_os_str()));
                            break;
                        }
                    }
                }
            }
        }
        Ok(Self { roots: paths })
    }

    pub(crate) fn resolve_unreserved(&self, path: &Path) -> io::Result<PathBuf> {
        let requested = absolute_path(path)?;
        // Check the spelling first, even when a reserved file is missing or a
        // reserved symlink has become dangling.
        self.check(&requested)?;
        let resolved = resolve_path(&requested)?;
        self.check(&resolved)?;
        Ok(resolved)
    }

    /// Unlink/rename/create_new act on a directory entry, not on its symlink
    /// target. Resolve its parent fully, but do not dereference the final leaf.
    /// Never use this check for a read, truncate or ordinary write operation.
    pub(crate) fn resolve_entry_unreserved(&self, path: &Path) -> io::Result<PathBuf> {
        let requested = absolute_path(path)?;
        self.check(&requested)?;
        let parent = requested
            .parent()
            .ok_or_else(|| io::Error::other("entry has no parent"))?;
        let name = requested
            .file_name()
            .ok_or_else(|| io::Error::other("entry has no name"))?;
        let resolved = resolve_path(parent)?.join(name);
        self.check(&resolved)?;
        Ok(resolved)
    }

    fn check(&self, path: &Path) -> io::Result<()> {
        if self.roots.iter().any(|root| path.starts_with(root)) {
            return Err(io::Error::new(
                io::ErrorKind::PermissionDenied,
                "reserved native path",
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn root() -> PathBuf {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let root = std::env::temp_dir().join(format!(
            "readest-reserved-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir_all(&root).unwrap();
        root
    }

    #[test]
    fn reserves_exact_roots_and_new_descendants_not_similar_names() {
        let root = root();
        let private = root.join("local-ovis-private");
        let policy = ReservedPaths::new([private.clone()]).unwrap();
        for path in [&private, &private.join("job/input.pdf")] {
            assert_eq!(
                policy.resolve_unreserved(path).unwrap_err().kind(),
                io::ErrorKind::PermissionDenied
            );
        }
        for path in [
            root.join("local-ovis-private-copy/a.pdf"),
            root.join("Readest/book.pdf"),
        ] {
            assert_eq!(policy.resolve_unreserved(&path).unwrap(), path);
        }
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn rejects_relative_and_parent_components() {
        let policy = ReservedPaths::new([std::env::temp_dir().join("reserved-proof")]).unwrap();
        for path in ["relative.pdf", "/tmp/Readest/../private.pdf"] {
            assert!(policy.resolve_unreserved(Path::new(path)).is_err());
        }
        assert!(ReservedPaths::new([PathBuf::from("relative")]).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn resolves_existing_and_missing_targets_below_an_alias() {
        let root = root();
        let private = root.join("private");
        std::fs::create_dir(&private).unwrap();
        std::fs::write(private.join("old.pdf"), b"private").unwrap();
        std::os::unix::fs::symlink(&private, root.join("alias")).unwrap();
        std::os::unix::fs::symlink(private.join("old.pdf"), root.join("file.pdf")).unwrap();
        let policy = ReservedPaths::new([private]).unwrap();
        for path in ["alias/old.pdf", "alias/new/next.pdf", "file.pdf"] {
            assert!(policy.resolve_unreserved(&root.join(path)).is_err());
        }
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn reserved_root_alias_and_unrelated_dangling_link_are_distinguished() {
        let root = root();
        let actual = root.join("actual");
        std::fs::create_dir(&actual).unwrap();
        std::os::unix::fs::symlink(&actual, root.join("private")).unwrap();
        let policy = ReservedPaths::new([root.join("private")]).unwrap();
        assert!(policy.resolve_unreserved(&actual.join("new.pdf")).is_err());
        assert!(policy
            .resolve_unreserved(&root.join("private/new.pdf"))
            .is_err());
        std::os::unix::fs::symlink(root.join("missing"), root.join("dangling")).unwrap();
        assert_eq!(
            policy
                .resolve_unreserved(&root.join("dangling/new.pdf"))
                .unwrap(),
            root.join("missing/new.pdf")
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn a_dangling_resource_root_does_not_break_an_unrelated_book() {
        let root = root();
        std::fs::create_dir(root.join("resources")).unwrap();
        std::os::unix::fs::symlink("../future-runtime", root.join("resources/local-ovis")).unwrap();
        let policy = ReservedPaths::new([root.join("resources/local-ovis")]).unwrap();
        assert_eq!(
            policy
                .resolve_unreserved(&root.join("books/book.epub"))
                .unwrap(),
            root.join("books/book.epub")
        );
        assert!(policy
            .resolve_unreserved(&root.join("resources/local-ovis/job"))
            .is_err());
        assert!(policy
            .resolve_unreserved(&root.join("future-runtime/job"))
            .is_err());
        assert!(!root.join("future-runtime").exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn entry_operations_do_not_grant_following_a_leaf_link() {
        let root = root();
        std::fs::create_dir(root.join("private")).unwrap();
        std::fs::write(root.join("private/file"), b"unchanged").unwrap();
        std::os::unix::fs::symlink(root.join("private/file"), root.join("book.part")).unwrap();
        let policy = ReservedPaths::new([root.join("private")]).unwrap();
        assert!(policy.resolve_unreserved(&root.join("book.part")).is_err());
        assert!(policy
            .resolve_entry_unreserved(&root.join("book.part"))
            .is_ok());
        std::os::unix::fs::symlink(root.join("private"), root.join("parent")).unwrap();
        assert!(policy
            .resolve_entry_unreserved(&root.join("parent/new.part"))
            .is_err());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn a_loop_in_a_reserved_root_does_not_reserve_its_siblings() {
        let root = root();
        std::os::unix::fs::symlink("local-ovis-private", root.join("local-ovis-private")).unwrap();
        let policy = ReservedPaths::new([root.join("local-ovis-private")]).unwrap();
        assert_eq!(
            policy
                .resolve_unreserved(&root.join("books/book.epub"))
                .unwrap(),
            root.join("books/book.epub")
        );
        assert!(policy
            .resolve_unreserved(&root.join("local-ovis-private/input.pdf"))
            .is_err());
        std::os::unix::fs::symlink(root.join("local-ovis-private"), root.join("alias")).unwrap();
        assert!(policy
            .resolve_unreserved(&root.join("alias/input.pdf"))
            .is_err());
        std::fs::remove_dir_all(root).unwrap();
    }
}
