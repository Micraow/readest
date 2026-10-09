/** Small DOM helpers; deterministic tests are not browser interaction acceptance. */
export function selectParagraph(layer,status) {
 const doc=layer.ownerDocument,selection=doc.getSelection();
 if(!layer.isConnected||!selection){status.textContent='当前段落已更新，请重新选择。';return false;}
 selection.removeAllRanges();const range=doc.createRange();range.selectNodeContents(layer);selection.addRange(range);
 status.textContent=layer.querySelector('[data-unresolved]')?'已选中本段；含未确认文字或公式，复制会被拒绝。可回原页核对。':'已选中本段。按 Ctrl+C 或 Command+C 复制实验映射正文。';
 return true;
}
export function createDialogController(dialog,title,focusArea,closeButton,fallbackFocus) {
 let opener=null;
 const cleanup=()=>{focusArea.replaceChildren();title.textContent='';const target=opener?.isConnected?opener:fallbackFocus;opener=null;target?.focus();};
 const cleanupIfClosed=()=>{if(!dialog.open&&(opener||focusArea.childNodes.length))cleanup();};
 const close=()=>{if(dialog.open)dialog.close();cleanupIfClosed();};
 dialog.addEventListener('close',cleanupIfClosed);
 closeButton.onclick=close;
 return {
  open(text,node,trigger=dialog.ownerDocument.activeElement){if(!dialog.open)opener=trigger;title.textContent=text;focusArea.replaceChildren(node);if(!dialog.open)dialog.showModal();closeButton.focus();},
  close,
  reset(){if(dialog.open)close();else {focusArea.replaceChildren();title.textContent='';opener=null;}},
 };
}
