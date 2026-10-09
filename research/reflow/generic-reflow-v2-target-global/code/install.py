"""Explicit adapter for a separately versioned local native asset service."""
import hashlib,importlib.util,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def install_global_renderer():
    import asset_service
    spec=importlib.util.spec_from_file_location('target_global_request',HERE/'render_request.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    old=asset_service.renderer_identity;tag=hashlib.sha256(b''.join((HERE/n).read_bytes() for n in ['device_alpha.py','render_request.py','install.py'])).hexdigest()
    def identity(version):return old(version)+';direct-global-target:'+tag
    asset_service.renderer_identity=identity;module.renderer_identity=identity;asset_service.run=module.run
    return {'version':tag,'global_reference_required':True,'local_crop_rendering_removed':True}
