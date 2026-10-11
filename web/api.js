export async function api(path, body){
  const response=await fetch(path, body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok) throw Error(data.error||JSON.stringify(data.detail||data));
  return data;
}
export function el(tag, props={}, ...children){
  const node=document.createElement(tag);
  for(const [k,v] of Object.entries(props)){
    if(k.startsWith('on'))node.addEventListener(k.slice(2).toLowerCase(),v);
    else if(k==='class')node.className=v;
    else if(k in node)node[k]=v;
    else node.setAttribute(k,v);
  }
  for(const child of children.flat())if(child!==null&&child!==undefined)node.append(child instanceof Node?child:document.createTextNode(String(child)));
  return node;
}
export function field(text,input){return el('label',{},text,input)}
export function select(items,value){return el('select',{},items.map(i=>el('option',{value:typeof i==='string'?i:i.value,selected:(typeof i==='string'?i:i.value)===String(value)},typeof i==='string'?i:i.label)))}
export function download(name,value){const link=el('a',{href:URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})),download:name});link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}
