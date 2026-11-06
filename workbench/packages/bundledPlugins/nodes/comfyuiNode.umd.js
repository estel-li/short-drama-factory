/*! toonflowNode:{"displayName":"ComfyUI 工作流","author":"Local Plugin","github":"","configRules":[],"version":"0.10.3","readme":"导入本地 ComfyUI 工作流，管理 H3 参考、模型预检与任务状态。连接使用设置中的 MiniMax H3 / ComfyUI 地址；生产缓存与续跑使用本地 H3 工厂节点。"} */
(function (root, factory) {
  if (typeof exports === "object" && typeof module !== "undefined") {
    module.exports = factory(require("vue"), require("@vue-flow/core"), require("element-plus"));
  } else if (typeof define === "function" && define.amd) {
    define(["vue", "@vue-flow/core", "element-plus"], factory);
  } else {
    root.toonflowNodes = root.toonflowNodes || {};
    root.toonflowNodes.comfyuiNode = factory(root.toonflowNodeHost.vue, root.toonflowNodeHost.vueFlow, root.toonflowNodeHost.elementPlus);
  }
})(this, function (Vue, VueFlow, ElementPlus) {
  const { defineComponent, ref, computed, h, watchEffect, nextTick } = Vue;
  const { useNode, useVueFlow } = VueFlow;
  /*! Official Toonflow node scaffold d7366e36ba30943cf308121c28011b45bbf922e0
MIT License

Copyright (c) 2026 HBAI-Ltd

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/
var nodeScaffold=(function(v,e,M,w){"use strict";var q={outline:{xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round"},filled:{xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"currentColor",stroke:"none"}};const C=(n,s,r,u)=>({color:y="currentColor",size:d=24,stroke:a=2,title:b,class:p,...f},{attrs:l,slots:m})=>{let h=[...u.map(N=>e.h(...N)),...m.default?[m.default()]:[]];return b&&(h=[e.h("title",b),...h]),e.h("svg",{...q[n],width:d,height:d,...l,class:["tabler-icon",`tabler-icon-${s}`],...n==="filled"?{fill:y}:{"stroke-width":a??q[n]["stroke-width"],stroke:y},...f},h)};var xe=C("outline","box","Box",[["path",{d:"M12 3l8 4.5l0 9l-8 4.5l-8 -4.5l0 -9l8 -4.5",key:"svg-0"}],["path",{d:"M12 12l8 -4.5",key:"svg-1"}],["path",{d:"M12 12l0 9",key:"svg-2"}],["path",{d:"M12 12l-8 -4.5",key:"svg-3"}]]);var Be=C("outline","circle-dashed","CircleDashed",[["path",{d:"M8.56 3.69a9 9 0 0 0 -2.92 1.95",key:"svg-0"}],["path",{d:"M3.69 8.56a9 9 0 0 0 -.69 3.44",key:"svg-1"}],["path",{d:"M3.69 15.44a9 9 0 0 0 1.95 2.92",key:"svg-2"}],["path",{d:"M8.56 20.31a9 9 0 0 0 3.44 .69",key:"svg-3"}],["path",{d:"M15.44 20.31a9 9 0 0 0 2.92 -1.95",key:"svg-4"}],["path",{d:"M20.31 15.44a9 9 0 0 0 .69 -3.44",key:"svg-5"}],["path",{d:"M20.31 8.56a9 9 0 0 0 -1.95 -2.92",key:"svg-6"}],["path",{d:"M15.44 3.69a9 9 0 0 0 -3.44 -.69",key:"svg-7"}]]);var Ve=C("outline","circle-dot","CircleDot",[["path",{d:"M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",key:"svg-0"}],["path",{d:"M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0",key:"svg-1"}]]);var ve=C("outline","copy-plus","CopyPlus",[["path",{d:"M7 9.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z",key:"svg-1"}],["path",{d:"M4.012 16.737a2 2 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1",key:"svg-2"}],["path",{d:"M11 14h6",key:"svg-3"}],["path",{d:"M14 11v6",key:"svg-4"}]]);var Q=C("outline","copy","Copy",[["path",{d:"M7 7m0 2.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z",key:"svg-0"}],["path",{d:"M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1",key:"svg-1"}]]);var Oe=C("outline","download","Download",[["path",{d:"M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2",key:"svg-0"}],["path",{d:"M7 11l5 5l5 -5",key:"svg-1"}],["path",{d:"M12 4l0 12",key:"svg-2"}]]);var _=C("outline","folder-plus","FolderPlus",[["path",{d:"M12 19h-7a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2h4l3 3h7a2 2 0 0 1 2 2v3.5",key:"svg-0"}],["path",{d:"M16 19h6",key:"svg-1"}],["path",{d:"M19 16v6",key:"svg-2"}]]);var De=C("outline","loader-2","Loader2",[["path",{d:"M12 3a9 9 0 1 0 9 9",key:"svg-0"}]]);var ze=C("outline","maximize","Maximize",[["path",{d:"M4 8v-2a2 2 0 0 1 2 -2h2",key:"svg-0"}],["path",{d:"M4 16v2a2 2 0 0 0 2 2h2",key:"svg-1"}],["path",{d:"M16 4h2a2 2 0 0 1 2 2v2",key:"svg-2"}],["path",{d:"M16 20h2a2 2 0 0 0 2 -2v-2",key:"svg-3"}]]);var Ae=C("outline","refresh","Refresh",[["path",{d:"M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4",key:"svg-0"}],["path",{d:"M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4",key:"svg-1"}]]);var ee=C("outline","trash","Trash",[["path",{d:"M4 7l16 0",key:"svg-0"}],["path",{d:"M10 11l0 6",key:"svg-1"}],["path",{d:"M14 11l0 6",key:"svg-2"}],["path",{d:"M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12",key:"svg-3"}],["path",{d:"M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3",key:"svg-4"}]]);function te(n){const s=Array.isArray(n)?n:[n];return s.every(r=>typeof r=="string")?s.flatMap(r=>r.split(",")).map(r=>r.trim()).filter(Boolean):[]}function O(n,s){const r=te(n),u=te(s);return r.length>0&&u.length>0&&(r.includes("*")||u.includes("*")||r.some(y=>u.includes(y)))}const oe=(n,s)=>{if(n.source===n.target)return!1;const{sourceNode:r,targetNode:u}=s,y=Array.isArray(r?.data.handles)?r.data.handles:[],d=Array.isArray(u?.data.handles)?u.data.handles:[],a=y.find(p=>p?.id===n.sourceHandle&&p.type==="source"),b=d.find(p=>p?.id===n.targetHandle&&p.type==="target");if(!a||!b||!O(a.dataType,b.dataType))return!1;try{return!u.isValidTargetPos||u.isValidTargetPos(n,s)===!0}catch(p){return console.error("节点连接校验失败",p),!1}};function $e(n){if(!n||typeof n!="object"||!("dataType"in n)||!("value"in n))return!1;const{dataType:s,value:r}=n;switch(s){case"STRING":return typeof r=="string";case"BOOLEAN":return typeof r=="boolean";case"INT":return typeof r=="number"&&Number.isSafeInteger(r);case"FLOAT":return typeof r=="number"&&Number.isFinite(r);case"IMAGE":case"MASK":case"VIDEO":case"AUDIO":case"FILE":{const u=s==="MASK"?"image":s.toLowerCase();return!!r&&typeof r=="object"&&"url"in r&&typeof r.url=="string"&&!!r.url.trim()&&"mimeType"in r&&typeof r.mimeType=="string"&&(s==="FILE"?/^[^/\s]+\/[^/\s]+$/.test(r.mimeType):r.mimeType.startsWith(`${u}/`)&&r.mimeType.length>u.length+1)}default:return!1}}function D(n,s){return Array.isArray(n)?n.find(r=>r.id===s):n.get(s)}function ne(n,s,r,u){const y=D(r,n)?.data?.handles?.find(d=>d.type==="target"&&d.id===s);return y?u.filter(d=>d.target===n&&d.targetHandle===s).flatMap(d=>{const a=D(r,d.source),b=a?.data?.handles?.find(p=>p.type==="source"&&p.id===d.sourceHandle);return a&&b&&O(b.dataType,y.dataType)?[{node:a,handle:b}]:[]}):[]}function ie(n,s){const r=n.data?.outputs;if(!r)return;const u=r[s.id];if(!(u===void 0||!Object.hasOwn(r,s.id))){if(!$e(u)||!O(u.dataType,s.dataType))throw new Error(`节点 ${n.id} 的输出端口 ${s.id} 值不符合类型声明`);return u}}function Ie(n,s,r){const u=D(r,n),y=u?.data?.handles?.find(d=>d.type==="source"&&d.id===s);return u&&y?ie(u,y):void 0}function Re(n,s,r,u){const y=D(r,n)?.data?.handles?.find(d=>d.type==="target"&&d.id===s);return y?ne(n,s,r,u).flatMap(({node:d,handle:a})=>{const b=ie(d,a);return b?O(b.dataType,y.dataType)?[{...b,source:d.id,sourceHandle:a.id}]:[]:[{source:d.id,sourceHandle:a.id,dataType:a.dataType,value:void 0}]}):[]}const K=Symbol.for("toonflow.targetEdges");function He(n=M.useVueFlow()){const s=n,{nodeLookup:r}=n,u=s[K]??e.computed(()=>Map.groupBy(n.getEdges.value,y=>y.target));return s[K]||Object.defineProperty(s,K,{value:u}),{getTargetSources:(y,d)=>ne(y,d,r.value,u.value.get(y)??[]),getTargetValues:(y,d)=>Re(y,d,r.value,u.value.get(y)??[]),getSourceValue:(y,d)=>Ie(y,d,r.value)}}const W=Symbol.for("toonflow.nodeEvents");function Pe(n=M.useNodeId(),s=M.useVueFlow()){if(!n)throw new Error("请在节点组件中使用 useNodeEvent()，或传入节点 ID");const{getSourceValue:r,getTargetValues:u}=He(s),y=s,d=y[W]??new Map;y[W]||Object.defineProperty(y,W,{value:d});function a(p,f){if(p.startsWith("input:"))return e.watch(()=>u(n,p.slice(6)),N=>f(N),{deep:!0,immediate:!0});if(p.startsWith("output:"))return e.watch(()=>r(n,p.slice(7)),N=>f(N),{deep:!0,immediate:!0});if(p!=="delete"&&p!=="save"&&p!=="copy"&&p!=="canConnect")throw new Error(`未知节点事件：${p}`);let l=d.get(n);l||(l={delete:new Set,save:new Set,copy:new Set,canConnect:new Set},d.set(n,l));const m=l[p];m.add(f);const h=()=>{m.delete(f)&&!l.delete.size&&!l.save.size&&!l.copy.size&&!l.canConnect.size&&d.delete(n)};return e.onScopeDispose(h),h}function b(...p){const f=d.get(n);return p[0]==="canConnect"?[...f?.canConnect??[]].every(l=>l(p[1],p[2])===!0):p[0]==="copy"?(async()=>{const l=s.findNode(n),m={};for(const h of[...f?.copy??[]])Object.assign(m,await h());if(s.findNode(n)!==l||d.get(n)!==f)throw new Error("节点已切换，请重新复制");return m})():(async()=>{if(p[0]==="delete"){const l=s.findNode(n);for(const m of[...f?.save??[]])await m();if(s.findNode(n)!==l||d.get(n)!==f)throw new Error("节点已切换，请重新操作")}for(const l of[...f?.[p[0]]??[]])p[0]==="save"&&p[1]?await l(p[1]):await l()})()}return{on:a,emit:b}}const Le={class:"titleBar"},je=["tabindex","title","onKeydown"],Fe={class:"cardContainer"},Ke={key:0,class:"loadingContent",role:"status","aria-label":"节点加载中"},We=((n,s)=>{const r=n.__vccOpts||n;for(const[u,y]of s)r[u]=y;return r})(e.defineComponent({inheritAttrs:!1,__name:"nodeSkeleton",props:e.mergeModels({label:{default:"未命名节点"},handles:{default:()=>[]},outputs:{default:()=>({})},icon:{},loading:{type:Boolean},readOnly:{type:Boolean,default:!1},previewReady:{type:Boolean,default:!0},topWidth:{default:"20vw"},bottomWidth:{default:"20vw"},downloadUrl:{},downloadName:{},fullscreenVisible:{type:Boolean,default:!0}},{topVisible:{type:Boolean,default:!1},topVisibleModifiers:{},bottomVisible:{type:Boolean,default:!1},bottomVisibleModifiers:{}}),emits:e.mergeModels(["fullscreen"],["update:topVisible","update:bottomVisible"]),setup(n,{emit:s}){const r=e.useModel(n,"topVisible"),u=e.useModel(n,"bottomVisible"),y=s,d=e.ref(!1),a=n,b=e.computed(()=>[{type:"target",position:M.Position.Left,items:a.handles.filter(o=>o.type==="target")},{type:"source",position:M.Position.Right,items:a.handles.filter(o=>o.type==="source")}]),p=e.computed(()=>Math.max(100,...b.value.map(o=>(o.items.length+1)*44))),{id:f,node:l}=M.useNode(),m=e.inject("nodeDocument",void 0),h=e.computed(()=>a.readOnly?void 0:m?.targets.get(f)),N=e.ref(),ae=e.shallowRef();let z;function U(o){if(a.readOnly)throw new Error("只读节点不能挂载到工作区文档");const t=N.value;if(!m||!t||!o.isConnected)throw new Error("节点视图尚未就绪");h.value||(ae.value={width:`${t.offsetWidth||l.dimensions.width||220}px`,height:`${t.offsetHeight||l.dimensions.height||128}px`});const i=Symbol();return z=i,m.targets.set(f,o),()=>{z===i&&(z=void 0,m.targets.delete(f),e.nextTick(()=>{h.value||se([f])}))}}e.watch(()=>a.loading,o=>{a.readOnly||(o?m?.mounts.get(f)===U&&m.mounts.delete(f):m?.mounts.set(f,U))},{immediate:!0}),e.onScopeDispose(()=>{z=void 0,m?.mounts.get(f)===U&&(m.mounts.delete(f),m.targets.delete(f))});const le=e.inject("selectionConnection",void 0),A=Pe();a.readOnly||(l.isValidTargetPos=(...o)=>!a.readOnly&&A.emit("canConnect",...o));const{d3Zoom:re,d3Selection:J,zoomActivationKeyCode:Ue,zoomOnPinch:Je,setViewport:Xe,minZoom:Ye,maxZoom:Ge,viewport:X,vueFlowRef:Ze,addNodes:qe,addEdges:Qe,toObject:_e,getNodes:et,getSelectedNodes:tt,findNode:$,addSelectedNodes:ot,removeSelectedElements:nt,removeNodes:it,removeEdges:at,updateNodeInternals:se,screenToFlowCoordinate:de,connectionLookup:ce,connectionStartHandle:fe,connectionEndHandle:ue,connectionStatus:lt,onPaneClick:rt,onPaneContextMenu:st,onSelectionContextMenu:dt,onConnectStart:ct,onMoveStart:ft,onNodeContextMenu:ut,onNodeDragStart:pt,onNodeClick:yt,onSelectionStart:ht}=M.useVueFlow(),pe=e.inject("batchCanvasHistory",void 0),ye=e.computed(()=>{const o=typeof l.style=="function"?l.style(l):l.style;return a.readOnly||h.value?{}:{...o?.width?{width:o.width}:{},...o?.height?{height:o.height}:{}}}),T=e.shallowRef();function gt(o){if(a.readOnly||a.loading||h.value||o.button!==0||T.value)return;const t=o.currentTarget,i=N.value;if(!i)return;const c=()=>new Promise(k=>{T.value={element:t,pointerId:o.pointerId,point:de({x:o.clientX,y:o.clientY}),width:i.offsetWidth,height:i.offsetHeight,resolve:k},l.resizing=!0,t.setPointerCapture(o.pointerId)});(pe?pe(c):c()).catch(k=>{x(),w.ElMessage.error(k instanceof Error?k.message:"节点缩放失败")})}function he(o,t){const i=N.value?.querySelector(".titleBar")?.offsetHeight??32,c=typeof l.style=="function"?l.style(l):l.style;l.style={...c,width:`${Math.max(160,o)}px`,height:`${Math.max(p.value+i,t)}px`}}function wt(o){const t=T.value;if(!t||o.pointerId!==t.pointerId)return;if(a.readOnly||a.loading||h.value||$(f)!==l)return x();const i=de({x:o.clientX,y:o.clientY});he(t.width+i.x-t.point.x,t.height+i.y-t.point.y)}function x(o){const t=T.value;!t||o&&o.pointerId!==t.pointerId||(T.value=void 0,l.resizing=!1,t.element.hasPointerCapture(t.pointerId)&&t.element.releasePointerCapture(t.pointerId),t.resolve())}function mt(o){if(a.readOnly||a.loading||h.value||T.value)return;const t=N.value;if(!t||!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(o.key))return;o.preventDefault();const i=o.key==="ArrowLeft"?-10:o.key==="ArrowRight"?10:0,c=o.key==="ArrowUp"?-10:o.key==="ArrowDown"?10:0;he(t.offsetWidth+i,t.offsetHeight+c)}e.onScopeDispose(()=>x()),e.watch(()=>[a.readOnly,a.loading,h.value],()=>x());const ge=e.computed(()=>fe.value?.nodeId===f?fe.value:void 0),kt=e.computed(()=>ue.value?.nodeId===f?ue.value:void 0),bt=e.computed(()=>le?.value?.nodeId===f?le.value:void 0),Mt=e.computed(o=>{const t=new Set(a.handles.filter(i=>ce.value.get(`${f}-${i.type}-${i.id}`)?.size).map(i=>`${i.type}-${i.id}`));return o?.size===t.size&&[...t].every(i=>o.has(i))?o:t});async function Ct(o){if(h.value)return;const t=o.currentTarget;await e.nextTick();const i=Ze.value;if(!i||!t.isConnected)return;const c=i.getBoundingClientRect();if(c.width<=0||c.height<=0)return;const k=[t,...t.querySelectorAll(":scope > .floatingSlot")].filter(E=>E.getClientRects().length).map(E=>E.getBoundingClientRect()),B=Math.min(...k.map(E=>E.left)),g=Math.min(...k.map(E=>E.top)),Z=M.pointToRendererPoint({x:B-c.left,y:g-c.top},X.value),Vt=M.getTransformForBounds({...Z,width:(Math.max(...k.map(E=>E.right))-B)/X.value.zoom,height:(Math.max(...k.map(E=>E.bottom))-g)/X.value.zoom},c.width,c.height,Ye.value,Ge.value,.2);await Xe(Vt,{duration:300})}function Nt(o){if(h.value||document.fullscreenElement||!(Ue.value===!0||o.ctrlKey&&Je.value)||!re.value||!J.value)return;const t=J.value.node()?.getBoundingClientRect();t&&(o.preventDefault(),o.stopPropagation(),re.value.scaleBy(J.value,2**M.wheelDelta(o),[o.clientX-t.left,o.clientY-t.top]))}const I=e.ref(!1),we=e.computed(()=>!I.value&&(!l.selected||tt.value.length<=1));ht(()=>{I.value=!0}),pt(({nodes:o})=>{o.some(t=>t.id===f)&&(I.value=!0)}),yt(({node:o})=>{o.id===f&&(I.value=!1)});const V=e.ref(!1),R=e.ref(""),me=e.ref(),Y=e.inject("reloadRemoteNode",void 0),H=e.ref(!1),P=e.ref(!1),S=e.ref(),ke=e.shallowRef({getBoundingClientRect:()=>new DOMRect});rt(()=>S.value?.handleClose()),st(()=>S.value?.handleClose()),dt(()=>S.value?.handleClose()),ct(()=>S.value?.handleClose()),ft(()=>S.value?.handleClose()),ut(({event:o,node:t})=>{t.id===f?be(o):S.value?.handleClose()});async function Et(){if(!(a.readOnly||!Y||H.value)){H.value=!0;try{await Y(l.type)}catch(o){w.ElMessage.error(o instanceof Error?o.message:"节点刷新失败")}finally{H.value=!1}}}async function be(o){if(a.readOnly)return;o.preventDefault(),h.value&&o.stopPropagation(),S.value?.handleClose();const t="changedTouches"in o?o.changedTouches[0]:o;t&&(ke.value={getBoundingClientRect:()=>new DOMRect(t.clientX,t.clientY,0,0)},await e.nextTick(),S.value?.handleOpen())}async function Me(){if(!(a.readOnly||P.value)){P.value=!0;try{await A.emit("delete"),it(f)}catch(o){const t=o?.response?.data?.message;w.ElMessage.error(t||(o instanceof Error?o.message:"节点删除失败"))}finally{P.value=!1}}}const G=e.inject("copyNodeToClipboard",void 0),L=e.ref(!1),j=e.inject("saveNodeToAssets",void 0),F=e.computed(()=>a.handles.flatMap(o=>{const t=a.outputs[o.id];return o.type!=="source"||!t||t.dataType==="STRING"&&!t.value.trim()?[]:[{label:o.label??o.id,output:t}]}));async function Ce(o){if(!a.readOnly){if(o==="saveAsset"&&j?.(a.label,F.value),o==="clipboard"&&G&&!L.value){L.value=!0;try{const t=await A.emit("copy"),i={...l.data,...t};await G({type:l.type,data:i}),w.ElMessage.success("已复制到剪贴板")}catch(t){w.ElMessage.error(t instanceof Error?t.message:"节点复制失败")}finally{L.value=!1}}if(o==="delete"&&Me(),o==="copy"||o==="duplicate"){let t;try{const g=await A.emit("copy");t=JSON.parse(JSON.stringify({...l.data,...g}))}catch(g){w.ElMessage.error(g instanceof Error?g.message:"节点复制失败");return}if($(f)!==l)return;const i=crypto.randomUUID(),c=o==="duplicate"?_e().edges.filter(g=>g.target===f):[],k={x:l.position.x,y:l.position.y+l.dimensions.height+32},B=et.value.filter(g=>g.parentNode===l.parentNode&&g.position.x<k.x+l.dimensions.width&&g.position.x+g.dimensions.width>k.x).sort((g,Z)=>g.position.y-Z.position.y);for(const g of B)k.y<g.position.y+g.dimensions.height+32&&k.y+l.dimensions.height+32>g.position.y&&(k.y=g.position.y+g.dimensions.height+32);nt(),qe({id:i,zIndex:l.zIndex,type:l.type,position:k,data:{...t,label:`${a.label} - 副本`},parentNode:l.parentNode}),await e.nextTick(),ot([$(i)]),Qe(c.map(g=>({...JSON.parse(JSON.stringify(g)),id:crypto.randomUUID(),target:i,selected:!1})))}}}async function Ne(){a.readOnly||(R.value=a.label,V.value=!0,await e.nextTick(),me.value?.select())}function Ee(){if(a.readOnly||!V.value)return;const o=R.value.trim();o&&(l.data.label=o),V.value=!1}function St(o){a.readOnly||o.isComposing||(o.preventDefault(),Ee())}function Tt(o){if(o.pointerType==="touch")return;const t=o.currentTarget,i=t.getBoundingClientRect();if(!i.width||!i.height)return;const c=(o.clientX-i.left-i.width/2)/i.width*18,k=(o.clientY-i.top-i.height/2)/i.height*18,B=Math.min(.3,6/(Math.hypot(c,k)||1));t.style.setProperty("--handleX",`${c*B}px`),t.style.setProperty("--handleY",`${k*B}px`)}function Se(o){const t=o.currentTarget;t.style.removeProperty("--handleX"),t.style.removeProperty("--handleY")}function Te(o){return Mt.value.has(`${o.type}-${o.id}`)}function xt(o){const t=ce.value.get(`${f}-${o.type}-${o.id}`);if(!t?.size)return!1;if(l.selected||l.dragging)return!0;for(const i of t.values()){const c=$(o.type==="source"?i.target:i.source);if(c?.selected||c?.dragging)return!0}return!1}function Bt(o){const t=bt.value;if(t?.handles.some(c=>c.id===o.id&&c.type===o.type))return t.status;const i=kt.value;return i?.id===o.id&&i.type===o.type?lt.value:null}return e.watchEffect(()=>{a.readOnly||a.loading||JSON.stringify(l.data.handles)!==JSON.stringify(a.handles)&&(l.data.handles=a.handles.map(o=>({...o})))}),e.watchEffect(()=>{a.readOnly||a.loading||(l.data.outputs=a.outputs)}),e.watch(()=>JSON.stringify([a.label,a.handles,a.readOnly]),()=>{a.readOnly||a.loading||(at(o=>o.filter(t=>t.source===f&&!a.handles.some(i=>i.type==="source"&&i.id===t.sourceHandle)||t.target===f&&!a.handles.some(i=>i.type==="target"&&i.id===t.targetHandle))),h.value||se([f]))},{flush:"post"}),(o,t)=>(e.openBlock(),e.createElementBlock(e.Fragment,null,[h.value?(e.openBlock(),e.createElementBlock("div",{key:0,class:"nodeDocumentPlaceholder",style:e.normalizeStyle(ae.value),"aria-hidden":"true"},null,4)):e.createCommentVNode("v-if",!0),(e.openBlock(),e.createBlock(e.Teleport,{to:h.value??"body",disabled:!h.value},[e.createElementVNode("div",e.mergeProps({ref_key:"skeletonElement",ref:N},o.$attrs,{class:["nodeSkeleton",{documentNode:h.value,resized:!!ye.value.height,resizing:!!T.value}],style:ye.value,onWheelCapture:Nt,onDblclick:e.withModifiers(Ct,["stop"]),onContextmenu:t[27]||(t[27]=i=>h.value&&be(i))}),[n.readOnly?e.createCommentVNode("v-if",!0):(e.openBlock(),e.createBlock(e.unref(w.ElDropdown),{key:0,ref_key:"menu",ref:S,trigger:"contextmenu",virtualTriggering:"",virtualRef:ke.value,placement:"bottom-start",showArrow:!1,showTimeout:0,hideTimeout:0,onCommand:Ce},{dropdown:e.withCtx(()=>[e.createVNode(e.unref(w.ElDropdownMenu),null,{default:e.withCtx(()=>[F.value.length&&e.unref(j)?(e.openBlock(),e.createBlock(e.unref(w.ElDropdownItem),{key:0,command:"saveAsset",icon:e.unref(_)},{default:e.withCtx(()=>[...t[28]||(t[28]=[e.createTextVNode("保存到素材库",-1)])]),_:1},8,["icon"])):e.createCommentVNode("v-if",!0),e.createVNode(e.unref(w.ElDropdownItem),{divided:!!(F.value.length&&e.unref(j)),command:"copy",icon:e.unref(Q)},{default:e.withCtx(()=>[...t[29]||(t[29]=[e.createTextVNode("复制节点",-1)])]),_:1},8,["divided","icon"]),e.createVNode(e.unref(w.ElDropdownItem),{command:"duplicate",icon:e.unref(ve)},{default:e.withCtx(()=>[...t[30]||(t[30]=[e.createTextVNode("创建副本",-1)])]),_:1},8,["icon"]),e.createVNode(e.unref(w.ElDropdownItem),{command:"delete",icon:e.unref(ee)},{default:e.withCtx(()=>[...t[31]||(t[31]=[e.createTextVNode("删除节点",-1)])]),_:1},8,["icon"]),e.createVNode(e.unref(w.ElDropdownItem),{divided:"",command:"clipboard",icon:e.unref(Q),disabled:!e.unref(G)||L.value},{default:e.withCtx(()=>[...t[32]||(t[32]=[e.createTextVNode(" 复制到剪贴板 ",-1)])]),_:1},8,["icon","disabled"])]),_:1})]),_:1},8,["virtualRef"])),!n.readOnly&&(h.value||r.value&&we.value)?(e.openBlock(),e.createElementBlock("div",{key:1,class:"floatingSlot topSlot nodrag nopan nowheel",style:e.normalizeStyle({width:typeof n.topWidth=="number"?`${n.topWidth}px`:n.topWidth}),onPointerdown:t[4]||(t[4]=e.withModifiers(()=>{},["stop"])),onMousedown:t[5]||(t[5]=e.withModifiers(()=>{},["stop"])),onDblclick:t[6]||(t[6]=e.withModifiers(()=>{},["stop"])),onKeydown:t[7]||(t[7]=e.withModifiers(()=>{},["stop"])),onContextmenu:t[8]||(t[8]=e.withModifiers(()=>{},["stop"]))},[e.renderSlot(o.$slots,"top",{},()=>[e.createVNode(e.unref(w.ElCard),{class:"mediaToolbar",shadow:"never",bodyStyle:{padding:"6px"}},{default:e.withCtx(()=>[e.createVNode(e.unref(w.ElButton),{icon:e.unref(_),disabled:!F.value.length||!e.unref(j),text:"",title:"添加到素材库","aria-label":"添加到素材库",onClick:t[0]||(t[0]=e.withModifiers(i=>Ce("saveAsset"),["stop"]))},{default:e.withCtx(()=>[...t[33]||(t[33]=[e.createTextVNode("添加到素材库",-1)])]),_:1},8,["icon","disabled"]),e.renderSlot(o.$slots,"topActions",{},void 0,!0),e.createVNode(e.unref(w.ElDivider),{direction:"vertical"}),e.renderSlot(o.$slots,"topRightActions",{},void 0,!0),e.createVNode(e.unref(w.ElButton),{tag:n.downloadUrl?"a":"button",href:n.downloadUrl||void 0,download:n.downloadName,icon:e.unref(Oe),disabled:!n.downloadUrl,loading:d.value,"aria-busy":d.value,text:"",title:d.value?"正在保存…":"下载","aria-label":"下载",onDownloadstate:t[1]||(t[1]=i=>d.value=i.detail),onClick:t[2]||(t[2]=e.withModifiers(()=>{},["stop"]))},null,8,["tag","href","download","icon","disabled","loading","aria-busy","title"]),n.fullscreenVisible?(e.openBlock(),e.createBlock(e.unref(w.ElButton),{key:0,icon:e.unref(ze),disabled:!n.downloadUrl,text:"",title:"全屏","aria-label":"全屏",onClick:t[3]||(t[3]=e.withModifiers(i=>y("fullscreen"),["stop"]))},null,8,["icon","disabled"])):e.createCommentVNode("v-if",!0)]),_:3})],!0)],36)):e.createCommentVNode("v-if",!0),!n.readOnly&&o.$slots.bottom&&(h.value||u.value&&we.value)?(e.openBlock(),e.createElementBlock("div",{key:2,class:"floatingSlot bottomSlot nodrag nopan nowheel",style:e.normalizeStyle({width:typeof n.bottomWidth=="number"?`${n.bottomWidth}px`:n.bottomWidth}),onPointerdown:t[9]||(t[9]=e.withModifiers(()=>{},["stop"])),onMousedown:t[10]||(t[10]=e.withModifiers(()=>{},["stop"])),onDblclick:t[11]||(t[11]=e.withModifiers(()=>{},["stop"])),onKeydown:t[12]||(t[12]=e.withModifiers(()=>{},["stop"])),onContextmenu:t[13]||(t[13]=e.withModifiers(()=>{},["stop"]))},[e.renderSlot(o.$slots,"bottom",{},void 0,!0)],36)):e.createCommentVNode("v-if",!0),e.withDirectives(e.createElementVNode("div",Le,[(e.openBlock(),e.createBlock(e.resolveDynamicComponent(n.icon??e.unref(xe)),{class:"titleIcon",size:16,"aria-hidden":"true"})),V.value&&!n.readOnly?e.withDirectives((e.openBlock(),e.createElementBlock("input",{key:0,ref_key:"labelInput",ref:me,"onUpdate:modelValue":t[14]||(t[14]=i=>R.value=i),class:"labelInput nodrag nopan","aria-label":"节点名称",onPointerdown:t[15]||(t[15]=e.withModifiers(()=>{},["stop"])),onMousedown:t[16]||(t[16]=e.withModifiers(()=>{},["stop"])),onDblclick:t[17]||(t[17]=e.withModifiers(()=>{},["stop"])),onKeydown:[t[18]||(t[18]=e.withModifiers(()=>{},["stop"])),e.withKeys(St,["enter"]),t[19]||(t[19]=e.withKeys(e.withModifiers(i=>V.value=!1,["prevent"]),["esc"]))],onBlur:Ee},null,544)),[[e.vModelText,R.value]]):(e.openBlock(),e.createElementBlock("span",{key:1,class:"labelText",tabindex:n.readOnly?void 0:0,title:n.readOnly?n.label:`${n.label}（双击编辑名称）`,onDblclick:t[20]||(t[20]=i=>!n.readOnly&&(i.stopPropagation(),Ne())),onKeydown:e.withKeys(e.withModifiers(Ne,["stop","prevent"]),["enter"])},e.toDisplayString(n.label),41,je)),n.readOnly?e.createCommentVNode("v-if",!0):(e.openBlock(),e.createElementBlock("div",{key:2,class:"nodeActions nodrag nopan",onPointerdown:t[21]||(t[21]=e.withModifiers(()=>{},["stop"])),onMousedown:t[22]||(t[22]=e.withModifiers(()=>{},["stop"])),onDblclick:t[23]||(t[23]=e.withModifiers(()=>{},["stop"]))},[e.createVNode(e.unref(w.ElButton),{icon:e.unref(Ae),loading:n.loading||H.value,disabled:n.loading||!e.unref(Y),text:"",title:"刷新节点","aria-label":"刷新节点",onClick:e.withModifiers(Et,["stop"])},null,8,["icon","loading","disabled"]),e.createVNode(e.unref(w.ElButton),{icon:e.unref(ee),text:"",title:"移除节点","aria-label":"移除节点",onClick:e.withModifiers(Me,["stop"]),loading:P.value},null,8,["icon","loading"])],32))],512),[[e.vShow,!h.value]]),e.createElementVNode("div",Fe,[e.createVNode(e.unref(w.ElCard),{class:e.normalizeClass(["contentCard",{selected:e.unref(l).selected}]),shadow:"never",bodyStyle:{padding:"8px"},style:e.normalizeStyle({minHeight:`${p.value}px`})},{default:e.withCtx(()=>[n.loading?(e.openBlock(),e.createElementBlock("div",Ke,[e.createVNode(e.unref(De),{class:"loadingIcon",size:24,"aria-hidden":"true"}),t[34]||(t[34]=e.createElementVNode("span",null,"加载中...",-1))])):n.previewReady||h.value?e.renderSlot(o.$slots,"default",{key:1},void 0,!0):e.createCommentVNode("v-if",!0)]),_:3},8,["class","style"]),(e.openBlock(!0),e.createElementBlock(e.Fragment,null,e.renderList(b.value,i=>(e.openBlock(),e.createElementBlock(e.Fragment,{key:i.type},[(e.openBlock(!0),e.createElementBlock(e.Fragment,null,e.renderList(i.items,(c,k)=>e.withDirectives((e.openBlock(),e.createBlock(e.unref(M.Handle),{id:c.id,key:c.id,class:e.normalizeClass(["nodeHandle",{connected:Te(c),connectedNodeActive:xt(c),linking:ge.value?.id===c.id&&ge.value.type===i.type}]),type:i.type,connectable:!n.readOnly&&!n.loading,position:i.position,isValidConnection:e.unref(oe),"data-connection-status":Bt(c),style:e.normalizeStyle({top:`${(k+1)/(i.items.length+1)*100}%`}),title:`${c.label??c.id} · ${Array.isArray(c.dataType)?c.dataType.join(" / "):c.dataType}`,"aria-label":`${c.label??c.id} · ${Array.isArray(c.dataType)?c.dataType.join(" / "):c.dataType}`,onPointermove:Tt,onPointerleave:Se,onPointercancel:Se},{default:e.withCtx(()=>[(e.openBlock(),e.createBlock(e.resolveDynamicComponent(Te(c)?e.unref(Ve):e.unref(Be)),{class:"handleIcon",size:18,"aria-hidden":"true"}))]),_:2},1032,["id","class","type","connectable","position","isValidConnection","data-connection-status","style","title","aria-label"])),[[e.vShow,!h.value]])),128))],64))),128)),!n.readOnly&&!n.loading&&!h.value?(e.openBlock(),e.createElementBlock("button",{key:0,class:"resizeCorner nodrag nopan",type:"button","aria-label":"调整节点大小（方向键微调）",onPointerdown:e.withModifiers(gt,["stop","prevent"]),onPointermove:e.withModifiers(wt,["stop"]),onPointerup:e.withModifiers(x,["stop"]),onPointercancel:x,onLostpointercapture:x,onKeydown:e.withModifiers(mt,["stop"]),onMousedown:t[24]||(t[24]=e.withModifiers(()=>{},["stop"])),onClick:t[25]||(t[25]=e.withModifiers(()=>{},["stop"])),onDblclick:t[26]||(t[26]=e.withModifiers(()=>{},["stop"]))},null,32)):e.createCommentVNode("v-if",!0)])],16)],8,["to","disabled"]))],64))}}),[["__scopeId","data-v-9e2d1973"]]);return v.nodeSkeleton=We,v.validateConnection=oe,Object.defineProperty(v,Symbol.toStringTag,{value:"Module"}),v})({},Vue,VueFlow,ElementPlus);

if (typeof document !== "undefined" && !document.getElementById("comfyuiNodeScaffoldStyle")) { const style = document.createElement("style"); style.id = "comfyuiNodeScaffoldStyle"; style.textContent = ".nodeSkeleton[data-v-9e2d1973]{position:relative;width:220px;color:var(--el-text-color-primary);text-align:left}.nodeSkeleton.resized[data-v-9e2d1973]{display:flex;flex-direction:column}.nodeSkeleton.resized .titleBar[data-v-9e2d1973]{flex-shrink:0}.nodeSkeleton.resized .cardContainer[data-v-9e2d1973]{flex:1;min-height:0}.nodeSkeleton.resized .cardContainer .contentCard[data-v-9e2d1973]{height:100%;box-sizing:border-box}.nodeSkeleton.resized .cardContainer .contentCard [data-v-9e2d1973] .el-card__body{height:100%;box-sizing:border-box;overflow:auto}.nodeSkeleton.documentNode[data-v-9e2d1973]{display:flex;flex-direction:column;gap:16px;width:100%!important;min-width:0}.nodeSkeleton.documentNode .floatingSlot[data-v-9e2d1973]{position:static;width:100%!important;transform:none}.nodeSkeleton.documentNode .floatingSlot.topSlot[data-v-9e2d1973]{order:0}.nodeSkeleton.documentNode .floatingSlot.bottomSlot[data-v-9e2d1973]{order:2}.nodeSkeleton.documentNode .cardContainer[data-v-9e2d1973]{order:1;min-width:0}.nodeSkeleton:hover .cardContainer .nodeHandle .handleIcon[data-v-9e2d1973]{opacity:1}.nodeSkeleton:hover .titleBar .nodeActions[data-v-9e2d1973]{visibility:visible}:is(.nodeSkeleton:hover,.nodeSkeleton.resizing) .cardContainer .resizeCorner[data-v-9e2d1973]{opacity:.55}.nodeSkeleton .floatingSlot[data-v-9e2d1973]{position:absolute;left:50%;z-index:2;transform:translate(-50%)}.nodeSkeleton .floatingSlot.topSlot[data-v-9e2d1973]{bottom:calc(100% + 12px)}.nodeSkeleton .floatingSlot.bottomSlot[data-v-9e2d1973]{top:calc(100% + 12px)}.nodeSkeleton .floatingSlot .mediaToolbar[data-v-9e2d1973] .el-button{width:auto;min-width:32px;height:32px;margin:0;padding:0 8px;text-decoration:none}.nodeSkeleton .titleBar[data-v-9e2d1973]{display:flex;align-items:center;gap:6px;padding:0 4px 8px;font-size:14px;line-height:20px}.nodeSkeleton .titleBar .titleIcon[data-v-9e2d1973]{flex-shrink:0}.nodeSkeleton .titleBar .labelText[data-v-9e2d1973]{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:grab;-webkit-user-select:none;user-select:none}.nodeSkeleton .titleBar .labelText[data-v-9e2d1973]:active{cursor:grabbing}.nodeSkeleton .titleBar .labelInput[data-v-9e2d1973]{flex:1;min-width:0;width:100%;padding:0 4px;border:1px solid var(--el-color-primary);border-radius:var(--el-border-radius-small);outline:none;background:var(--el-bg-color);color:inherit;font:inherit;line-height:inherit}.nodeSkeleton .titleBar .nodeActions[data-v-9e2d1973]{visibility:hidden;display:flex;flex-shrink:0;gap:2px}.nodeSkeleton .titleBar .nodeActions .el-button[data-v-9e2d1973]{width:24px;height:24px;margin:0;padding:0}.nodeSkeleton .cardContainer[data-v-9e2d1973]{position:relative}.nodeSkeleton .cardContainer .resizeCorner[data-v-9e2d1973]{position:absolute;right:calc(var(--ui-radius-large, var(--el-border-radius-base)) * .293 - 2px);bottom:calc(var(--ui-radius-large, var(--el-border-radius-base)) * .293 - 2px);transform:translate(50%,50%);box-sizing:border-box;width:4px;height:4px;padding:0;border:1px solid var(--el-border-color);border-radius:1px;background:var(--el-bg-color);opacity:0;cursor:nwse-resize;touch-action:none}.nodeSkeleton .cardContainer .resizeCorner[data-v-9e2d1973]:before{content:\"\";position:absolute;inset:-4px}.nodeSkeleton .cardContainer .resizeCorner[data-v-9e2d1973]:focus-visible{opacity:1}.nodeSkeleton .cardContainer .contentCard.selected[data-v-9e2d1973]{border-color:color-mix(in srgb,var(--el-color-primary) 50%,var(--el-border-color-light))}.nodeSkeleton .cardContainer .contentCard .loadingContent[data-v-9e2d1973]{display:flex;min-height:84px;align-items:center;justify-content:center;gap:8px;color:var(--el-text-color-secondary);font-size:12px}.nodeSkeleton .cardContainer .contentCard .loadingContent .loadingIcon[data-v-9e2d1973]{color:var(--el-color-primary);animation:nodeLoading-9e2d1973 1s linear infinite}@media(prefers-reduced-motion:reduce){.nodeSkeleton .cardContainer .contentCard .loadingContent .loadingIcon[data-v-9e2d1973]{animation:none}}.nodeSkeleton .cardContainer .nodeHandle[data-v-9e2d1973]{display:flex;align-items:center;justify-content:center;width:18px;height:18px;border:0;background:transparent;color:var(--el-text-color-secondary)}.nodeSkeleton .cardContainer .nodeHandle.vue-flow__handle-left[data-v-9e2d1973]{left:-12px}.nodeSkeleton .cardContainer .nodeHandle.vue-flow__handle-right[data-v-9e2d1973]{right:-12px}.nodeSkeleton .cardContainer .nodeHandle[data-v-9e2d1973]:before{content:\"\";position:absolute;inset:-13px;border-radius:50%}.nodeSkeleton .cardContainer .nodeHandle .handleIcon[data-v-9e2d1973]{pointer-events:none;opacity:0;transform:translate(var(--handleX, 0px),var(--handleY, 0px));transition:transform .12s ease-out,opacity .12s ease-out}.nodeSkeleton .cardContainer .nodeHandle.connected .handleIcon[data-v-9e2d1973],.nodeSkeleton .cardContainer .nodeHandle.linking .handleIcon[data-v-9e2d1973],.nodeSkeleton .cardContainer .nodeHandle.connecting .handleIcon[data-v-9e2d1973],.nodeSkeleton .cardContainer .nodeHandle[data-connection-status] .handleIcon[data-v-9e2d1973]{opacity:1}.nodeSkeleton .cardContainer .nodeHandle[data-v-9e2d1973]:hover,.nodeSkeleton .cardContainer .nodeHandle.linking[data-v-9e2d1973],.nodeSkeleton .cardContainer .nodeHandle.connecting[data-v-9e2d1973],.nodeSkeleton .cardContainer .nodeHandle[data-connection-status=valid][data-v-9e2d1973]{color:var(--el-color-primary)}.nodeSkeleton .cardContainer .nodeHandle[data-connection-status=invalid][data-v-9e2d1973]{color:var(--el-color-danger);cursor:not-allowed}@media(prefers-reduced-motion:reduce){.nodeSkeleton .cardContainer .nodeHandle .handleIcon[data-v-9e2d1973]{transform:none;transition:none}}@keyframes nodeLoading-9e2d1973{to{transform:rotate(360deg)}}\n"; document.head.appendChild(style); }
  const { nodeSkeleton } = nodeScaffold;
  function createWorkflowCore() {
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const clone = v => JSON.parse(JSON.stringify(v));
  const safe = k => !["__proto__", "prototype", "constructor"].includes(k);
  const NONE_OPTION = "none";
  const h3ReferenceLimits = { image: 9, audio: 3, video: 1 };
  const kinds = { IMAGE: "image", AUDIO: "audio", VIDEO: "video" };
  const names = { image: "图片", audio: "音频", video: "视频", text: "提示词" };
  const fields = {
    ckpt_name: "基础模型", unet_name: "扩散模型", model_name: "模型", clip_name: "文本编码模型", vae_name: "VAE 模型",
    lora_name: "LoRA", strength_model: "LoRA 模型强度", strength_clip: "LoRA 文本强度",
    width: "宽度", height: "高度", aspect_ratio: "画幅", resolution: "分辨率", megapixels: "分辨率（百万像素）",
    duration: "时长（秒）", seconds: "时长（秒）", length: "帧数 / 长度", num_frames: "帧数",
    frames: "帧数", frame_rate: "帧率", fps: "帧率", steps: "步数", extra_steps: "附加步数",
    seed: "种子", noise_seed: "噪声种子", cfg: "CFG", guidance: "引导强度", denoise: "降噪强度",
    sampler_name: "采样器", scheduler: "调度器", voice: "音色", voice_id: "音色", gender: "性别",
    speaker: "说话人", style: "风格", language: "语言", speed: "语速", pitch: "音调", batch_size: "批量",
    multiple: "尺寸倍数", weight_dtype: "模型精度", ref_image_size: "参考图尺寸"
  };
  const aliases = {
    checkpoint: "ckpt_name", checkpoint_name: "ckpt_name", ckpt: "ckpt_name",
    unet: "unet_name", diffusion_model: "unet_name", diffusion_model_name: "unet_name",
    model: "model_name", clip: "clip_name", vae: "vae_name",
    image_width: "width", video_width: "width", output_width: "width", target_width: "width",
    image_height: "height", video_height: "height", output_height: "height", target_height: "height",
    aspectratio: "aspect_ratio", duration_seconds: "duration", duration_sec: "duration",
    num_steps: "steps", sampling_steps: "steps", inference_steps: "steps", num_inference_steps: "steps",
    frame_count: "num_frames", total_frames: "num_frames"
  };
  const primaryFields = new Set(["ckpt_name", "unet_name", "model_name", "clip_name", "vae_name",
    "lora_name", "strength_model", "strength_clip", "width", "height", "aspect_ratio", "resolution",
    "megapixels", "duration", "seconds", "length", "num_frames", "frames", "frame_rate", "fps", "steps"]);
  const helperNode = /resize|scale|crop|pad|tile|preprocess|preview|display|loadimage|loadvideo|load_audio|loadaudio/i;
  const fieldOrder = Object.keys(fields);
  const secret = /api.?key|token|password|secret|authorization|credential/i;
  const isLink = (v, w) => Array.isArray(v) && v.length === 2 && own(w, String(v[0])) && Number.isInteger(v[1]) && v[1] >= 0;
  function parseWorkflow(text) {
    let w = typeof text === "string" ? JSON.parse(text) : clone(text);
    if (w?.prompt && !w.prompt.class_type) w = w.prompt;
    if (!w || typeof w !== "object" || Array.isArray(w) || !Object.keys(w).length ||
        !Object.entries(w).every(([id, n]) => safe(id) && n && typeof n.class_type === "string" &&
          n.inputs && typeof n.inputs === "object" && !Array.isArray(n.inputs))) {
      throw new Error("请导入 API Format JSON，不是 ComfyUI 画布 JSON");
    }
    return w;
  }
  function formatNodeErrors(errors) {
    return Object.entries(errors || {}).flatMap(([id, node]) => {
      const reasons = node.errors?.length ? node.errors : [{ message: "节点校验未通过" }];
      return reasons.map(reason => {
        const detail = reason.type === "required_input_missing"
          ? `缺少必填参数 ${reason.extra_info?.input_name || reason.details || ""}`
          : [reason.message || reason.type || "校验失败", reason.details].filter(Boolean).join("：");
        return `节点 ${id}${node.class_type ? `（${node.class_type}）` : ""}：${detail}`;
      });
    }).join("\n");
  }
  function inputTarget(w, nodeId, path) {
    if (!safe(String(nodeId)) || !own(w, nodeId)) throw new Error(`节点 ${nodeId} 不存在`);
    let target = w[nodeId].inputs;
    const parts = String(path || "").split(".");
    if (!parts.length || parts.some(p => !p || !safe(p))) throw new Error(`字段路径不合法：${path}`);
    // ComfyUI autogrow inputs use literal dotted keys, not nested objects.
    if (own(target, path)) return [target, path];
    for (const p of parts.slice(0, -1)) {
      if (!own(target, p) || !target[p] || typeof target[p] !== "object") throw new Error(`节点 ${nodeId} 没有字段 ${path}`);
      target = target[p];
    }
    if (!own(target, parts.at(-1))) throw new Error(`节点 ${nodeId} 没有字段 ${path}`);
    return [target, parts.at(-1)];
  }
  function readInput(w, id, path) { const [o, k] = inputTarget(w, id, path); return o[k]; }
  function writeInput(w, id, path, v) { const [o, k] = inputTarget(w, id, path); o[k] = v; }
  function schemaFields(s) { return { ...s?.input?.required, ...s?.input?.optional }; }
  function isH3ReferenceNode(node, infos = {}) {
    return /^MiniMaxH3ReferenceToVideo$/i.test(node.class_type) ||
      /^MiniMaxH3ReferenceToVideo$/i.test(infos[node.class_type]?.name || "");
  }
  function isH3ReferenceWorkflow(w, infos = {}) {
    return Object.values(w).some(node => isH3ReferenceNode(node, infos));
  }
  function spec(s) {
    const meta = s?.[1] || {};
    return { type: Array.isArray(s?.[0]) ? "COMBO" : s?.[0], ...meta,
      options: Array.isArray(s?.[0]) ? s[0] : meta.options };
  }
  function scalar(v) { return ["string", "number", "boolean"].includes(typeof v); }
  function modelField(path) {
    return ["ckpt_name", "unet_name", "model_name", "clip_name", "vae_name", "lora_name"].includes(
      /^clip_name[123]$/.test(path) ? "clip_name" : aliases[path] || path);
  }
  function resolveModelFiles(w, infos = {}, replacements = {}) {
    const updates = [], issues = [];
    const normalized = value => value.replace(/\\/g, "/").toLowerCase();
    for (const [nodeId, node] of Object.entries(w)) for (const [path, value] of Object.entries(node.inputs)) {
      if (!modelField(path) || typeof value !== "string") continue;
      const options = spec(schemaFields(infos[node.class_type])[path]).options;
      if (!options || options.includes(value)) continue;
      const wanted = replacements[path]?.[value] || value;
      const exact = options.filter(v => typeof v === "string" && normalized(v) === normalized(wanted));
      const basename = normalized(wanted).split("/").at(-1);
      const sameFile = exact.length ? exact : options.filter(v =>
        typeof v === "string" && normalized(v).split("/").at(-1) === basename);
      if (sameFile.length === 1) {
        updates.push({ nodeId, path, previous: value, value: sameFile[0] });
      } else issues.push(`节点 ${nodeId} ${fields[path] || path}：${value}${sameFile.length > 1 ? " 有多个同名文件，需重新选择" : " 未安装或已更名，需选择本机文件"}`);
    }
    if (issues.length) throw new Error(`模型文件预检失败（未上传、未提交）：\n${issues.join("\n")}`);
    for (const update of updates) w[update.nodeId].inputs[update.path] = update.value;
    return updates;
  }
  function fillRequiredDefaults(w, infos = {}) {
    const filled = [];
    for (const [nodeId, node] of Object.entries(w)) {
      for (const [path, definition] of Object.entries(infos[node.class_type]?.input?.required || {})) {
        if (!safe(path) || own(node.inputs, path) || secret.test(path)) continue;
        const s = spec(definition), value = s.default;
        if (!scalar(value) || s.forceInput || s.defaultInput || fileKind(node.class_type, path, definition) ||
            promptField(node, path, value, w)) continue;
        const valid = s.type === "BOOLEAN" ? typeof value === "boolean" :
          s.type === "STRING" ? typeof value === "string" :
          s.type === "COMBO" ? s.options?.includes(value) :
          ["INT", "FLOAT"].includes(s.type) && typeof value === "number" && Number.isFinite(value) &&
            (s.type !== "INT" || Number.isSafeInteger(value)) &&
            (s.min === undefined || value >= s.min) && (s.max === undefined || value <= s.max);
        if (!valid) continue;
        node.inputs[path] = value;
        filled.push({ nodeId, path, value });
      }
    }
    return filled;
  }
  function validateRequiredInputs(w, infos = {}) {
    const errors = {};
    for (const [nodeId, node] of Object.entries(w)) {
      for (const [path, definition] of Object.entries(infos[node.class_type]?.input?.required || {})) {
        // Autogrow groups are serialized as flattened slots, not a group input.
        if (spec(definition).type === "COMFY_AUTOGROW_V3" || own(node.inputs, path)) continue;
        errors[nodeId] ??= { class_type: node.class_type, errors: [] };
        errors[nodeId].errors.push({ type: "required_input_missing", extra_info: { input_name: path } });
      }
    }
    const message = formatNodeErrors(errors);
    if (message) throw new Error(`工作流预检失败（未提交）：\n${message}`);
    return w;
  }
  function fileKind(type, path, schema) {
    const s = spec(schema);
    if (s.image_upload || /LoadImage/i.test(type) && /image/i.test(path)) return "image";
    if (s.audio_upload || /LoadAudio/i.test(type) && /audio/i.test(path)) return "audio";
    if (s.video_upload || /(?:LoadVideo|VHS_LoadVideo)/i.test(type) && /^(video|file|path)$/.test(path)) return "video";
    return null;
  }
  function promptField(node, path, val, w) {
    return typeof val === "string" && !secret.test(path) &&
      (/^(?:positive|negative)?_?(?:prompt|text|lyrics|transcript|speech_text)$/i.test(path) &&
        !/Save|Preview|Display|Label/i.test(node.class_type) ||
        path === "value" && /String|Text/i.test(node.class_type) &&
        Object.values(w).some(n => Object.entries(n.inputs).some(([k, v]) => /prompt|text|lyrics/i.test(k) && isLink(v, w) && w[String(v[0])] === node)));
  }
  function consumerIndex(w) {
    const index = new Map();
    for (const [nodeId, node] of Object.entries(w)) for (const [path, value] of Object.entries(node.inputs)) {
      if (!isLink(value, w)) continue;
      const id = String(value[0]), list = index.get(id) || [];
      list.push({ nodeId, path, node }); index.set(id, list);
    }
    return index;
  }
  function consumers(index, id) {
    const seen = new Set([id]), queue = [id], result = [];
    for (let i = 0; i < queue.length; i++) for (const entry of index.get(queue[i]) || []) {
      result.push(entry);
      if (!seen.has(entry.nodeId)) { seen.add(entry.nodeId); queue.push(entry.nodeId); }
    }
    return result;
  }
  function bindingId(b) { return `${b.kind}:${b.mode || "file"}:${b.nodeId}:${b.path}`; }
  const noLora = value => typeof value === "string" && value.toLowerCase() === NONE_OPTION;
  function sortParameters(parameters) {
    return [...parameters].sort((a, b) => (a.tier === "advanced") - (b.tier === "advanced") ||
      (a.category ?? 5) - (b.category ?? 5) ||
      (a.groupOrder ?? 0) - (b.groupOrder ?? 0) || (a.order ?? 0) - (b.order ?? 0) ||
      String(a.nodeId).localeCompare(String(b.nodeId), undefined, { numeric: true }) ||
      String(a.path).localeCompare(String(b.path)));
  }
  function parameterRole(node, path) {
    const key = path.toLowerCase();
    const semantic = /^clip_name[123]$/.test(key) ? "clip_name" : aliases[key] || key;
    if (!own(fields, semantic)) return null;
    const auxiliary = helperNode.test(node.class_type) && /^(?:width|height|resolution|megapixels|duration|length|num_frames|frames|frame_rate|fps|steps)$/.test(semantic);
    const audioControl = /audio|speech|tts|music|sound|voice/i.test(node.class_type) &&
      /^(?:voice|voice_id|speaker|gender|language|speed|pitch|style)$/.test(semantic);
    return { semantic, tier: primaryFields.has(semantic) && !auxiliary || audioControl ? "primary" : "advanced" };
  }
  function detectOutputs(w, infos = {}) {
    const outputs = [];
    for (const [nodeId, node] of Object.entries(w)) {
      const info = infos[node.class_type], type = node.class_type;
      let kind = /(?:save|preview).*image|image.*(?:save|preview)/i.test(type) ? "image" :
        /VideoCombine|(?:save|preview).*video|video.*(?:save|preview)/i.test(type) ? "video" :
        /(?:save|preview).*audio|audio.*(?:save|preview)/i.test(type) ? "audio" : null;
      if (/VideoCombine/i.test(type) && /^image\//i.test(node.inputs.format || "")) kind = "image";
      if (!kind && info?.output_node) {
        const media = new Set(Object.values(schemaFields(info)).map(def => kinds[spec(def).type]).filter(Boolean));
        if (media.size === 1) kind = [...media][0];
      }
      if (kind) outputs.push({ nodeId, kind, classType: type, label: node._meta?.title || type, preview: /preview/i.test(type) });
    }
    return outputs.sort((a, b) => ["image", "video", "audio"].indexOf(a.kind) - ["image", "video", "audio"].indexOf(b.kind) ||
      String(a.nodeId).localeCompare(String(b.nodeId), undefined, { numeric: true }));
  }
  function detect(w, infos = {}, { includeAdvanced = false } = {}) {
    const parameters = [], bindings = [];
    const downstream = consumerIndex(w), outputs = detectOutputs(w, infos);
    const primarySize = Object.values(w).some(node => Object.keys(node.inputs).some(path => {
      const role = parameterRole(node, path);
      return role?.tier === "primary" && /^(?:width|height|resolution|megapixels)$/.test(role.semantic);
    }));
    function roleFor(nodeId, path) {
      const node = w[nodeId], role = parameterRole(node, path);
      // A final resize is the size control when this workflow has no generation-size node.
      if (role?.tier === "advanced" && !primarySize && /resize|scale/i.test(node.class_type) &&
          /^(?:width|height|resolution|megapixels)$/.test(role.semantic) &&
          downstream.get(nodeId)?.some(c => outputs.some(o => o.nodeId === c.nodeId && !o.preview))) {
        return { ...role, tier: "primary" };
      }
      return role;
    }
    const loraNodes = new Map(Object.entries(w)
      .filter(([, node]) => Object.keys(node.inputs || {}).some(path => path === "lora_name") ||
        /lora/i.test(node.class_type || ""))
      .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }))
      .map(([nodeId], index) => [nodeId, index + 1]));
    function parameterGroup(nodeId, semantic, path) {
      const loraIndex = loraNodes.get(nodeId);
      if (loraIndex) {
        const groupKey = `lora:${nodeId}`;
        const groupLabel = `LoRA ${loraIndex}`;
        const order = path === "lora_name" ? 0 : path === "strength_model" ? 1 : path === "strength_clip" ? 2 : 3;
        const label = path === "lora_name" ? groupLabel :
          path === "strength_model" ? `${groupLabel} 模型强度` :
          path === "strength_clip" ? `${groupLabel} 文本强度` : `${groupLabel} ${fields[semantic] || semantic}`;
        return { label, groupKey, groupLabel, category: 1, groupOrder: loraIndex, order };
      }
      const group = /^(?:model_name|ckpt_name|unet_name|clip_name|vae_name)$/.test(semantic) ? ["model", "模型分类", 0] :
        /width|height|aspect|resolution|megapixel|multiple|ref_image_size/.test(semantic) ? ["size", "画幅与分辨率", 100] :
        /duration|seconds|length|frames|fps|frame_rate/.test(semantic) ? ["timing", "时长与帧率", 200] :
        /steps|seed|cfg|guidance|sampler|scheduler|denoise/.test(semantic) ? ["sampling", "生成设置", 300] :
        /voice|speaker|gender|language|speed|pitch|style/.test(semantic) ? ["audio", "音频设置", 400] :
        ["other", "其它参数", 400];
      return { label: fields[semantic] || semantic, groupKey: group[0] === "model" ? `model:${semantic}` : group[0],
        groupLabel: group[1], category: group[2] / 100 + (group[2] ? 1 : 0), groupOrder: 0,
        order: fieldOrder.indexOf(semantic) };
    }
    for (const [nodeId, node] of Object.entries(w)) {
      const schema = schemaFields(infos[node.class_type]);
      const usedBy = consumers(downstream, nodeId);
      for (const [path, value] of Object.entries(node.inputs)) {
        if (secret.test(path) || !scalar(value)) continue;
        const s = spec(schema[path]);
        const kind = fileKind(node.class_type, path, schema[path]);
        if (kind || promptField(node, path, value, w)) {
          const negative = /negative|负面|负向/i.test(path + " " + node._meta?.title) ||
            usedBy.some(c => /negative/.test(c.path));
          bindings.push({ kind: kind || "text", mode: "file", nodeId, path, label: node._meta?.title || node.class_type, enabled: !negative });
          continue;
        }
        let role = roleFor(nodeId, path), roleNodeId = nodeId;
        if (path === "value" && /Primitive|Constant/i.test(node.class_type)) {
          const title = node._meta?.title || "";
          const targets = usedBy.map(c => ({ ...c, role: roleFor(c.nodeId, c.path) }))
            .filter(c => c.role).sort((a, b) => (a.role.tier === "advanced") - (b.role.tier === "advanced") ||
              fieldOrder.indexOf(a.role.semantic) - fieldOrder.indexOf(b.role.semantic) ||
              a.nodeId.localeCompare(b.nodeId, undefined, { numeric: true }));
          role = /duration|时长|秒/i.test(title) ? { semantic: "duration", tier: "primary" } :
            targets[0]?.role || { semantic: "value", tier: "advanced" };
          if (targets[0] && !/duration|时长|秒/i.test(title)) roleNodeId = targets[0].nodeId;
        }
        if (!role || !includeAdvanced && role.tier === "advanced") continue;
        const { semantic, tier } = role;
        const loraParameter = loraNodes.has(roleNodeId) && ["lora_name", "strength_model", "strength_clip"].includes(semantic);
        const group = parameterGroup(roleNodeId, semantic, semantic);
        const enumOptions = s.options?.filter(scalar);
        const options = loraParameter && path === "lora_name"
          ? [NONE_OPTION, ...new Set((enumOptions ?? [value]).filter(v => scalar(v) && !noLora(v)))]
          : enumOptions;
        const detectedType = options?.length ? "enum" : typeof value === "boolean" ? "boolean" : typeof value === "number" ? "number" : "text";
        parameters.push({
          key: `auto_${nodeId}_${path.replace(/\W/g, "_")}`, ...group, nodeId, path,
          type: detectedType,
          defaultValue: value, options, min: s.min, max: s.max,
          step: s.step, integer: s.type === "INT", sourceLabel: node._meta?.title || node.class_type,
          detectedType, detectedLabel: group.label, semantic, loraParameter, tier,
          ...(tier === "advanced" ? { visible: false } : {})
        });
      }
      // Only supported reference banks are expanded. Unknown graph structures stay fixed.
      for (const [path, definition] of Object.entries(schema)) {
        const s = spec(definition), t = s.template;
        if (s.type !== "COMFY_AUTOGROW_V3" || !t?.prefix || !Number.isFinite(t.max)) continue;
        const ref = Object.values(t.input?.required || {})[0]?.[0];
        const kind = /ref_image/.test(t.prefix) ? "image" : /ref_video_audio/.test(t.prefix) ? null :
          /ref_video/.test(t.prefix) ? "video" : /ref_audio/.test(t.prefix) ? "audio" : null;
        if (kind && ["IMAGE", "AUDIO"].includes(ref)) bindings.push({
          kind, mode: "slots", nodeId, path: `${path}.${t.prefix}`, label: node._meta?.title || node.class_type,
          enabled: true, capacity: t.max, max: isH3ReferenceNode(node, infos) ? Math.min(h3ReferenceLimits[kind], t.max) :
            kind === "video" ? Math.min(1, t.max) : t.max,
          companion: kind === "video" && schema.ref_video_audios ? "ref_video_audios.ref_video_audio_" : undefined
        });
      }
      for (const [prefix, kind] of [["ref_image_", "image"], ["ref_audio_", "audio"], ["ref_video_", "video"]]) {
        const keys = Object.keys(schema).filter(k => new RegExp(`^${prefix}\\d+$`).test(k));
        if (keys.length) bindings.push({
          kind, mode: "slots", nodeId, path: prefix, label: node._meta?.title || node.class_type,
          enabled: true, capacity: keys.length, max: isH3ReferenceNode(node, infos) ? Math.min(h3ReferenceLimits[kind], keys.length) :
            kind === "video" ? 1 : keys.length,
          companion: kind === "video" && schema.ref_video_audio_0 ? "ref_video_audio_" : undefined
        });
      }
    }
    // Loader files upstream of a multi-reference bank belong to that bank, not extra slots.
    const bankLoaders = new Set();
    for (const b of bindings.filter(b => b.mode === "slots")) {
      for (const [path, link] of Object.entries(w[b.nodeId].inputs)) {
        if (path.startsWith(b.path) && isLink(link, w)) {
          try { const trail = mediaTrail(w, link, b.kind, infos); bankLoaders.add(trail.at(-1).nodeId); } catch { /* retain unresolved loader for manual mapping */ }
        }
      }
    }
    const cleaned = bindings.filter(b => b.kind === "text" || b.mode === "slots" || !bankLoaders.has(b.nodeId))
      .map(b => ({ ...b, id: bindingId(b) })).sort((a, b) =>
        ["text", "image", "audio", "video"].indexOf(a.kind) - ["text", "image", "audio", "video"].indexOf(b.kind) ||
        a.nodeId.localeCompare(b.nodeId, undefined, { numeric: true }) || a.path.localeCompare(b.path));
    return {
      parameters: sortParameters(parameters),
      bindings: cleaned,
      outputs
    };
  }
  function updatedLabel(old, detected) {
    return !old.label || old.label === old.detectedLabel || old.label === (fields[detected.semantic] || detected.semantic)
      ? detected.label : old.label;
  }
  function prepareParameters(w, definitions) {
    const detected = new Map(detect(w, {}, { includeAdvanced: true }).parameters.map(p => [`${p.nodeId}:${p.path}`, p]));
    return definitions.map(old => {
      const p = detected.get(`${old.nodeId}:${old.path}`);
      const automatic = Boolean(old.detectedType || old.key?.startsWith("auto_"));
      if (!p) return { ...old, groupKey: `other:${old.nodeId}`, category: 5, groupOrder: 0, order: 0,
        tier: automatic ? "advanced" : "primary", ...(automatic && old.visible === undefined ? { visible: false } : {}) };
      const result = { ...old, label: updatedLabel(old, p), detectedLabel: p.detectedLabel, semantic: p.semantic,
        groupKey: p.groupKey, groupLabel: p.groupLabel, groupOrder: p.groupOrder, order: p.order,
        category: p.category, loraParameter: p.loraParameter, tier: automatic ? p.tier : "primary",
        ...(automatic && p.tier === "advanced" && old.visible === undefined ? { visible: false } : {}) };
      if (p.loraParameter && p.path === "lora_name") {
        result.options = [NONE_OPTION, ...new Set((old.options?.length ? old.options : p.options || [])
          .filter(v => scalar(v) && !noLora(v)))];
        result.type = "enum";
        if (noLora(result.defaultValue)) result.defaultValue = NONE_OPTION;
      }
      return result;
    });
  }
  function mergeDetection(previous, detected, ignored = [], id = p => `${p.nodeId}:${p.path}`) {
    const map = new Map(previous.map(p => [id(p), p]));
    for (const p of detected) {
      const old = map.get(id(p));
      if (!old && !ignored.includes(id(p))) map.set(id(p), p);
      else if (old?.detectedType) {
        const merged = { ...p, ...old, options: p.options, min: p.min, max: p.max, step: p.step,
          type: old.type === old.detectedType ? p.type : old.type, detectedType: p.detectedType,
          detectedLabel: p.detectedLabel, groupKey: p.groupKey, groupLabel: p.groupLabel,
          groupOrder: p.groupOrder, order: p.order, category: p.category, semantic: p.semantic, loraParameter: p.loraParameter,
          tier: p.tier };
        merged.label = updatedLabel(old, p);
        map.set(id(p), merged);
      }
    }
    return [...map.values()];
  }
  function bypassLoras(w, disabled, infos) {
    const nativePorts = {
      LoraLoader: ["model", "clip"], LoraLoaderModelOnly: ["model"],
      LoraLoaderBypass: ["model", "clip"], LoraLoaderBypassModelOnly: ["model"]
    };
    const routes = new Map();
    for (const nodeId of disabled) {
      const node = w[nodeId], info = infos[node.class_type];
      const ports = nativePorts[node.class_type];
      let replacements;
      if (ports) replacements = ports.map(path => node.inputs[path]);
      else {
        const choices = spec(schemaFields(info).lora_name).options;
        const nativeNone = choices?.find(noLora);
        if (nativeNone !== undefined) { node.inputs.lora_name = nativeNone; continue; }
        if (!info?.output?.length || info.output_node ||
            info.output.some(type => !["MODEL", "CLIP"].includes(type))) {
          throw new Error(`LoRA ${nodeId}（${node.class_type}）无法安全停用：需提供 MODEL/CLIP 输入输出定义或原生 none 选项`);
        }
        const inputs = schemaFields(info);
        replacements = info.output.map(type => {
          const candidates = Object.entries(inputs).filter(([path, definition]) =>
            spec(definition).type === type && isLink(node.inputs[path], w));
          if (candidates.length !== 1) throw new Error(`LoRA ${nodeId} 的 ${type} 上游不唯一，无法安全停用`);
          return node.inputs[candidates[0][0]];
        });
      }
      routes.set(nodeId, replacements);
    }
    function resolve(link, seen = new Set()) {
      const nodeId = String(link[0]);
      if (!routes.has(nodeId)) return [...link];
      if (seen.has(nodeId)) throw new Error(`LoRA ${nodeId} 的旁路连线存在循环`);
      const replacement = routes.get(nodeId)[link[1]];
      if (!isLink(replacement, w)) throw new Error(`LoRA ${nodeId} 的输出端口 ${link[1]} 缺少兼容的上游，无法安全停用`);
      return resolve(replacement, new Set([...seen, nodeId]));
    }
    function rewrite(value) {
      if (isLink(value, w)) return resolve(value);
      if (Array.isArray(value)) return value.map(rewrite);
      if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, rewrite(v)]));
      return value;
    }
    // Resolve all disabled chains before deleting nodes, including nested custom inputs.
    const rewritten = new Map(Object.entries(w).filter(([id]) => !routes.has(id))
      .map(([id, node]) => [id, rewrite(node.inputs)]));
    for (const [id, inputs] of rewritten) w[id].inputs = inputs;
    for (const id of routes.keys()) delete w[id];
  }
  function applyParameters(w, defs, values, infos = {}) {
    const keys = new Set();
    const disabledLoras = new Set();
    for (const d of defs) {
      if (d.path !== "lora_name") continue;
      const raw = own(values, d.key) ? values[d.key] : d.defaultValue;
      if (noLora(raw)) disabledLoras.add(String(d.nodeId));
    }
    for (const d of defs) {
      if (!d.nodeId || !d.path) throw new Error(`参数“${d.label}”的节点 ID / 字段未填写`);
      if (!d.key || keys.has(d.key) || !safe(d.key)) throw new Error(`参数键重复或不合法：${d.key}`);
      keys.add(d.key);
      const raw = own(values, d.key) ? values[d.key] : d.defaultValue;
      if (raw === undefined) continue;
      const current = readInput(w, d.nodeId, d.path);
      if (disabledLoras.has(String(d.nodeId)) && /^strength_(?:model|clip)$/.test(d.path)) continue;
      if (isLink(current, w)) throw new Error(`参数“${d.label}”指向连线，请绑定上游常量`);
      if (d.path === "lora_name" && noLora(raw)) continue;
      if (d.type === "enum" && d.options?.length && !d.options.includes(raw) &&
          !(modelField(d.path) && spec(schemaFields(infos[w[d.nodeId].class_type])[d.path]).options))
        throw new Error(`参数“${d.label}”不是有效选项`);
      let v = raw;
      if (d.type === "number") {
        if (raw === "" || raw === null || typeof raw === "boolean") throw new Error(`参数“${d.label}”需要数字`);
        v = Number(raw);
        if (!Number.isFinite(v) || d.integer && !Number.isSafeInteger(v)) throw new Error(`参数“${d.label}”不是有效${d.integer ? "整数" : "数字"}`);
        if (d.min !== undefined && v < d.min || d.max !== undefined && v > d.max) throw new Error(`参数“${d.label}”超出范围 ${d.min ?? ""} ~ ${d.max ?? ""}`);
      } else if (d.type === "boolean") {
        if (typeof raw !== "boolean") throw new Error(`参数“${d.label}”需要开关值`);
      } else if (d.type !== "enum") v = String(raw);
      writeInput(w, d.nodeId, d.path, v);
    }
    if (disabledLoras.size) bypassLoras(w, disabledLoras, infos);
    return w;
  }
  function edgeKey(e) { return encodeURIComponent(JSON.stringify([e.source, e.sourceHandle])); }
  function orderedEdges(nodes, edges, id) {
    const order = nodes.find(n => n.id === id)?.data?.referenceOrder?.in || [];
    const ranks = new Map(order.map((k, i) => [k, i]));
    return edges.filter(e => e.target === id && (!e.targetHandle || e.targetHandle === "in"))
      .sort((a, b) => (ranks.get(edgeKey(a)) ?? order.length) - (ranks.get(edgeKey(b)) ?? order.length));
  }
  function collectCanvas(nodes, edges, id) {
    const lookup = new Map(nodes.map(n => [n.id, n]));
    function expand(node, handle, seen = new Set()) {
      if (!node || seen.has(node.id)) return [];
      seen.add(node.id);
      const results = [];
      function push(out, index = "") {
        if (Array.isArray(out)) { out.forEach((v, i) => push(v, `${index}/${i}`)); return; }
        if (!out || typeof out !== "object") return;
        const type = out.dataType;
        if (Array.isArray(out.value)) { out.value.forEach((v, i) => push(v?.dataType ? v : { dataType: type, value: v }, `${index}/${i}`)); return; }
        const kind = kinds[type] || (type === "STRING" ? "text" : "");
        const value = out.value;
        if (!kind) return;
        if (kind === "text" && typeof value !== "string") return;
        const url = value?.url || (typeof value === "string" ? value : "");
        if (kind !== "text" && !url) return;
        results.push({ kind, text: kind === "text" ? value : undefined, url: kind !== "text" ? url : undefined,
          key: kind === "text" ? `${node.id}:${handle}${index}` : `${kind}:${url}`, source: node.id, handle,
          label: node.data?.label || names[kind], mimeType: value?.mimeType });
      }
      // The native text composer updates prompt before it updates the saved text output.
      const prompt = node.data?.prompt;
      if (/^(?:remote-)?textNode$/.test(node.type || "") && handle === "text" &&
          typeof prompt === "string" && prompt.trim()) {
        push({ dataType: "STRING", value: prompt });
      } else push(node.data?.outputs?.[handle]);
      if (!results.length) {
        for (const child of nodes.filter(n => (n.parentNode || n.parentId) === node.id)) {
          for (const port of Object.keys(child.data?.outputs || {})) results.push(...expand(child, port, new Set(seen)));
          if (!Object.keys(child.data?.outputs || {}).length) results.push(...expand(child, "", new Set(seen)));
        }
      }
      return results;
    }
    const refsFor = nodeId => orderedEdges(nodes, edges, nodeId).flatMap(e => expand(lookup.get(e.source), e.sourceHandle));
    const direct = refsFor(id);
    const texts = direct.filter(r => r.kind === "text").map(r => ({ ...r, scope: refsFor(r.source) }));
    const all = [...direct, ...texts.flatMap(r => r.scope)].filter(r => r.kind !== "text");
    const gallery = [...new Map(all.map(r => [r.key, r])).values()];
    const counters = { image: 0, audio: 0, video: 0 };
    gallery.forEach(r => { r.alias = `${names[r.kind]}${++counters[r.kind]}`; });
    return { gallery, texts, direct };
  }
  function referenceToken(key) { return `{{tfref:${encodeURIComponent(key)}}}`; }
  function promptSegments(text) {
    const parts = [], pattern = /\{\{tfref:([^}]+)\}\}/g;
    let start = 0;
    for (const match of String(text).matchAll(pattern)) {
      if (match.index > start) parts.push({ text: text.slice(start, match.index) });
      try { parts.push({ key: decodeURIComponent(match[1]) }); }
      catch { parts.push({ text: match[0] }); }
      start = match.index + match[0].length;
    }
    if (start < text.length) parts.push({ text: text.slice(start) });
    return parts;
  }
  function selectReferences(canvas, mode = "mentioned", nodePrompt = "") {
    const selected = [], seen = new Set();
    function add(r) {
      if (!seen.has(r.key)) { selected.push(r); seen.add(r.key); }
      return `@@TFREF${selected.findIndex(s => s.key === r.key)}@@`;
    }
    const aliases = new Map();
    for (const r of canvas.gallery) {
      for (const label of new Set([r.alias, r.label])) {
        if (!aliases.has(label)) aliases.set(label, []);
        aliases.get(label).push(r);
      }
    }
    function byName(label) {
      const matches = aliases.get(label) || [];
      if (matches.length !== 1) throw new Error(`@${label} ${matches.length ? "名称重复，请用图片/音频/视频编号" : "没有对应的画布连线素材"}`);
      return add(matches[0]);
    }
    function resolve(text, scope, depth = 0) {
      if (depth > 12) throw new Error("文字引用循环或层级过深");
      let v = text.replace(/\{\{tfref:([^}]+)\}\}/g, (_, encoded) => {
        let key;
        try { key = decodeURIComponent(encoded); } catch { throw new Error("素材引用标记损坏，请重新选择素材"); }
        const r = canvas.gallery.find(item => item.key === key);
        if (!r) throw new Error("提示词中的参考素材已断开或已更换，请重新连接并选择素材");
        return add(r);
      });
      v = v.replace(/\{\{ref\s+(\d+)\}\}/g, (_, n) => {
        const r = scope[Number(n) - 1];
        if (!r) throw new Error(`参考 ${n} 已断开，无法解析 @ 引用`);
        if (r.kind === "text") return resolve(r.text, [], depth + 1);
        return add(r);
      });
      v = v.replace(/@\{([^}]+)\}/g, (_, label) => byName(label));
      v = v.replace(/@(图片|图像|音频|视频|参考)\s*(\d+)/g, (_, kind, n) => {
        if (kind === "参考") {
          const r = scope[Number(n) - 1];
          if (!r || r.kind === "text") throw new Error(`参考 ${n} 不是可用媒体`);
          return add(r);
        }
        return byName(`${kind === "图像" ? "图片" : kind}${n}`);
      });
      // Named mentions are exact and boundary-delimited; email addresses are untouched.
      for (const label of [...aliases.keys()].sort((a, b) => b.length - a.length)) {
        const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        v = v.replace(new RegExp(`(^|[\\s，。；、（(])@${escaped}(?=$|[\\s，。；、）)！!?])`, "g"), (_, lead) => lead + byName(label));
      }
      if (/\{\{tfref:|@(?:图片|图像|音频|视频|参考)|@\{|(?:^|\s)@[^\s，。；、]+/.test(v.replace(/@@TFREF\d+@@/g, ""))) throw new Error("存在未解析的 @ 素材引用");
      return v;
    }
    const local = typeof nodePrompt === "string" && nodePrompt.trim();
    const text = local ? resolve(nodePrompt, canvas.gallery) : canvas.texts.map(t => {
      const resolved = resolve(t.text, t.scope.length ? t.scope : canvas.direct);
      // A text node's connected attachments are implicit unless its prompt selects a subset.
      if (!/@@TFREF\d+@@/.test(resolved)) t.scope.filter(r => r.kind !== "text").forEach(add);
      return resolved;
    }).join("\n");
    if (local && !/@@TFREF\d+@@/.test(text)) canvas.gallery.forEach(add);
    if (mode === "all") canvas.gallery.forEach(add);
    if (mode === "mentioned" && canvas.gallery.length && !selected.length) throw new Error("已连接参考素材，但提示词中没有 @ 引用；请在节点或文字节点填写提示词、选择参考素材，或切换为全部连线");
    const counters = { image: 0, audio: 0, video: 0 };
    const numbered = selected.map(r => ({ ...r, index: ++counters[r.kind] }));
    return { selected: numbered, text, counts: counters,
      renderText(h3, audioOffset = 0) { return text.replace(/@@TFREF(\d+)@@/g, (_, n) => {
        const r = numbered[Number(n)];
        return h3 ? `<${{ image: "Picture", audio: "Audio", video: "Video" }[r.kind]} ${r.index + (r.kind === "audio" ? audioOffset : 0)}>` : `${names[r.kind]}${r.index}`;
      }); } };
  }
  function canvasPrompt(canvas) {
    const selection = selectReferences(canvas, "all");
    return selection.text.replace(/@@TFREF(\d+)@@/g, (_, n) => referenceToken(selection.selected[Number(n)].key));
  }
  function validateBindings(w, bindings, selection) {
    const enabled = bindings.filter(b => b.enabled !== false);
    if (selection.text.trim() && !enabled.some(b => b.kind === "text")) throw new Error("工作流尚未绑定提示词入口，请先一键检测并确认提示词绑定");
    for (const b of enabled) {
      if (b.mode !== "slots") readInput(w, b.nodeId, b.path);
      else if (!own(w, b.nodeId) || !safe(b.path) || !/^[\w.]+_$/.test(b.path) ||
        !Number.isInteger(Number(b.max)) || Number(b.max) < 0 || Number(b.max) > b.capacity) throw new Error("参考素材槽位或数量上限不合法");
    }
    for (const kind of ["image", "audio", "video"]) {
      const bs = enabled.filter(b => b.kind === kind), slots = bs.filter(b => b.mode === "slots");
      const count = selection.counts[kind];
      if (isH3ReferenceWorkflow(w) && count > h3ReferenceLimits[kind])
        throw new Error(`MiniMax H3 ${names[kind]}引用 ${count} 个，上限 ${h3ReferenceLimits[kind]} 个；请删减参考连线或提示词中的 @ 引用`);
      const capacity = slots.length ? Math.min(...slots.map(b => Math.min(Number(b.max), b.capacity))) : bs.length;
      if (count > capacity) throw new Error(`${names[kind]}引用 ${count} 个，当前工作流上限 ${capacity || 0} 个；请删减参考连线或提示词中的 @ 引用，或配置对应入口`);
    }
    return enabled;
  }
  function mediaTrail(w, link, kind, infos, seen = new Set()) {
    if (!isLink(link, w) || seen.has(String(link[0]))) throw new Error("素材入口不是可识别的加载链");
    const id = String(link[0]), node = w[id]; seen.add(id);
    const defs = schemaFields(infos[node.class_type]);
    const file = Object.keys(node.inputs).find(p => fileKind(node.class_type, p, defs[p]) === kind);
    if (file) return [{ nodeId: id, file, output: link[1] }];
    const candidates = Object.entries(node.inputs).filter(([p, v]) => isLink(v, w) &&
      (/image|video|audio|frames|pixels/i.test(p) || kinds[spec(defs[p]).type] === kind));
    if (candidates.length !== 1) throw new Error(`节点 ${id} 的素材处理链无法自动识别`);
    const [path, next] = candidates[0];
    return [{ nodeId: id, path, output: link[1] }, ...mediaTrail(w, next, kind, infos, seen)];
  }
  function loaderFor(kind, infos) {
    const preferred = kind === "image" ? ["LoadImage"] : kind === "audio" ? ["LoadAudio", "LoadAudioUI"] : ["LoadVideoUI", "VHS_LoadVideo"];
    for (const type of preferred) {
      const s = infos[type]; if (!s) continue;
      const schema = schemaFields(s), path = Object.keys(schema).find(p => fileKind(type, p, schema[p]) === kind);
      const outputType = kind === "video" ? "IMAGE" : kind.toUpperCase();
      const output = s.output?.indexOf(outputType);
      if (!path || !(output >= 0)) continue;
      const inputs = {}; let valid = true;
      for (const [p, definition] of Object.entries(s.input?.required || {})) {
        if (p === path) { inputs[p] = ""; continue; }
        const d = spec(definition);
        if (d.default !== undefined) inputs[p] = d.default;
        else if (d.options?.length) inputs[p] = d.options[0];
        else { valid = false; break; }
      }
      if (valid) return { type, path, output, inputs, audioOutput: s.output?.indexOf("AUDIO") };
    }
    throw new Error(`本地 ComfyUI 缺少可自动绑定的${names[kind]}加载器`);
  }
  function bankKeys(inputs, prefix) {
    return Object.keys(inputs).filter(p => p.startsWith(prefix) && /^\d+$/.test(p.slice(prefix.length)))
      .sort((a, b) => Number(a.slice(prefix.length)) - Number(b.slice(prefix.length)));
  }
  function normalizeH3Bindings(w, bindings, infos = {}) {
    if (!isH3ReferenceWorkflow(w, infos)) return bindings;
    const banks = detect(w, infos).bindings.filter(b => b.mode === "slots" && isH3ReferenceNode(w[b.nodeId], infos));
    const replacedFiles = new Set();
    for (const b of banks) for (const path of bankKeys(w[b.nodeId].inputs, b.path)) {
      try {
        const loader = mediaTrail(w, w[b.nodeId].inputs[path], b.kind, infos).at(-1);
        replacedFiles.add(bindingId({ kind: b.kind, nodeId: loader.nodeId, path: loader.file }));
      } catch { /* Unresolved chains still fail in the graph preflight. */ }
    }
    for (const b of banks.filter(b => b.companion)) for (const path of bankKeys(w[b.nodeId].inputs, b.companion)) {
      try {
        const loader = mediaTrail(w, w[b.nodeId].inputs[path], "audio", infos).at(-1);
        replacedFiles.add(bindingId({ kind: "audio", nodeId: loader.nodeId, path: loader.file }));
      } catch { /* A video loader's own soundtrack is already covered by its video bank. */ }
    }
    const normalized = bindings.filter(b => !replacedFiles.has(bindingId(b))).map(b => ({ ...b }));
    for (const bank of banks) {
      const index = normalized.findIndex(b => bindingId(b) === bindingId(bank));
      const old = index >= 0 ? normalized[index] : {};
      const updated = { ...bank, ...old, capacity: bank.capacity,
        max: Math.min(Number(old.max ?? bank.max), bank.max), companion: bank.companion };
      if (index >= 0) normalized[index] = updated;
      else normalized.push(updated);
    }
    // Old H3 imports may have no detected prompt binding. Bind the real prompt field.
    if (!normalized.some(b => b.kind === "text")) {
      for (const [nodeId, node] of Object.entries(w)) if (isH3ReferenceNode(node, infos) && own(node.inputs, "prompt"))
        normalized.push({ kind: "text", mode: "file", nodeId, path: "prompt", enabled: true, label: node.class_type });
    }
    return normalized;
  }
  function renderPrompt(w, selection, infos = {}) {
    const nodes = Object.values(w).filter(node => isH3ReferenceNode(node, infos));
    // H3 numbers video soundtracks before standalone audio references.
    const offsets = new Set(nodes.map(node => bankKeys(node.inputs, "ref_video_audios.ref_video_audio_")
      .concat(bankKeys(node.inputs, "ref_video_audio_")).filter(path => {
        const index = path.match(/(\d+)$/)[1];
        return own(node.inputs, `ref_videos.ref_video_${index}`) || own(node.inputs, `ref_video_${index}`);
      }).length));
    if (selection.counts.audio && offsets.size > 1) throw new Error("多个 H3 节点的视频原声数量不同，无法统一音频引用编号；请拆分工作流");
    return selection.renderText(nodes.length > 0, selection.counts.audio ? [...offsets][0] || 0 : 0);
  }
  function applyCanvas(w, bindings, selection, uploads, infos = {}) {
    const normalized = normalizeH3Bindings(w, bindings, infos);
    const enabled = validateBindings(w, normalized, selection);
    let next = Math.max(0, ...Object.keys(w).map(k => Number(k)).filter(Number.isFinite)) + 1;
    const newId = () => { while (own(w, String(next))) next++; return String(next++); };
    const abandoned = new Set();
    for (const kind of ["image", "audio", "video"]) {
      const refs = selection.selected.filter(r => r.kind === kind);
      const bs = enabled.filter(b => b.kind === kind);
      const banks = normalized.filter(b => b.kind === kind && b.mode === "slots" &&
        (b.enabled !== false || isH3ReferenceNode(w[b.nodeId], infos)));
      if (!banks.length) {
        refs.forEach((r, i) => writeInput(w, bs[i].nodeId, bs[i].path, uploads[r.key]));
        // Never leave unselected imported reference files executing silently.
        if (refs.length < bs.length && (refs.length || selection.text.trim())) throw new Error(`${names[kind]}是固定 ${bs.length} 个入口的工作流，不能自动减少到 ${refs.length} 个；请删减绑定及工作流，或改为可变参考槽位`);
        continue;
      }
      for (const b of banks) {
        const input = w[b.nodeId].inputs;
        const keys = bankKeys(input, b.path);
        const templates = keys.map(p => input[p]);
        const trails = templates.map(link => mediaTrail(w, link, kind, infos));
        trails.forEach(t => t.forEach(n => abandoned.add(n.nodeId)));
        keys.forEach(p => delete input[p]);
        if (b.companion) bankKeys(input, b.companion).forEach(p => {
          const link = input[p];
          if (isLink(link, w) && !abandoned.has(String(link[0])))
            mediaTrail(w, link, "audio", infos).forEach(n => abandoned.add(n.nodeId));
          delete input[p];
        });
        (b.enabled === false ? [] : refs).forEach((r, i) => {
          let link, audio;
          const trail = trails[i] || trails[0];
          if (trail) {
            let downstream;
            // Clone only the media processing chain, keeping model / size dependencies unchanged.
            for (const item of [...trail].reverse()) {
              const id = newId(), n = clone(w[item.nodeId]);
              if (item.file) n.inputs[item.file] = uploads[r.key];
              else n.inputs[item.path] = downstream;
              w[id] = n; downstream = [id, item.output];
              if (item.file && kind === "video") {
                const ai = infos[n.class_type]?.output?.indexOf("AUDIO");
                if (ai >= 0) audio = [id, ai];
              }
            }
            link = downstream;
          } else {
            const loader = loaderFor(kind, infos), id = newId();
            w[id] = { class_type: loader.type, inputs: { ...loader.inputs, [loader.path]: uploads[r.key] } };
            link = [id, loader.output];
            if (loader.audioOutput >= 0) audio = [id, loader.audioOutput];
          }
          input[b.path + i] = link;
          if (b.companion && audio) input[b.companion + i] = audio;
        });
      }
    }
    for (const b of enabled.filter(b => b.kind === "text")) if (selection.text.trim())
      writeInput(w, b.nodeId, b.path, renderPrompt(w, selection, infos));
    // Old banks may feed preview-only branches. Remove those too, but reject shared live branches.
    const removable = new Set(abandoned);
    let changed = true;
    while (changed) {
      changed = false;
      for (const [id, n] of Object.entries(w)) if (/^Preview/.test(n.class_type) &&
          Object.values(n.inputs).some(v => isLink(v, w) && removable.has(String(v[0]))) && !removable.has(id)) {
        removable.add(id); changed = true;
      }
    }
    for (const [id, n] of Object.entries(w)) if (!removable.has(id) &&
      Object.values(n.inputs).some(v => isLink(v, w) && removable.has(String(v[0])))) {
      throw new Error(`原参考素材还被节点 ${id} 共用，不能自动剔除；请拆分共用分支后重试`);
    }
    for (const id of removable) delete w[id];
    return w;
  }
  return { parseWorkflow, formatNodeErrors, fillRequiredDefaults, validateRequiredInputs, resolveModelFiles, modelField,
    readInput, writeInput, isLink, detect, detectOutputs, prepareParameters, sortParameters, mergeDetection, applyParameters,
    collectCanvas, selectReferences, referenceToken, promptSegments, canvasPrompt,
    validateBindings, normalizeH3Bindings, isH3ReferenceWorkflow, renderPrompt,
    applyCanvas, mediaTrail, loaderFor, bindingId, clone, names, noneOption: NONE_OPTION };
}

  const Core = createWorkflowCore();
  // 保留工作流指定的模型文件名，由本机预检报告缺项。
  const modelFileReplacements = {};

  function unwrap(value) {
    if (typeof Vue?.unref === "function") return Vue.unref(value);
    return value && typeof value === "object" && "value" in value ? value.value : value;
  }

  function parseWorkflow(value) {
    return Core.parseWorkflow(value);
  }

  function outputEntries(item) {
    const entries = [];
    for (const [nodeId, node] of Object.entries(item?.outputs || {})) {
      for (const type of ["images", "videos", "audio", "gifs", "files"]) {
        for (const file of node?.[type] || []) entries.push({ nodeId, kind: type, ...file });
      }
    }
    return entries;
  }

  async function fetchJson(url, options = {}, timeoutMs = 20000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const target = options.method && options.method !== "GET" ? url.replace("/api/localModels/comfy/get/", "/api/localModels/comfy/post/") : url;
      const response = await fetch(target, { ...options, headers: { ...options.headers, "x-toonflow-workspace": "1" }, signal: controller.signal });
      const text = await response.text();
      let body;
      try { body = text ? JSON.parse(text) : {}; } catch { body = { raw: text }; }
      if (!response.ok) {
        const error = new Error(`${response.status} ${response.statusText}: ${Core.formatNodeErrors(body?.node_errors) || body?.error?.message || body?.raw || text}`);
        error.httpStatus = response.status;
        throw error;
      }
      return body;
    } finally { clearTimeout(timer); }
  }

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function replacePlaceholders(value, replacements) {
    if (typeof value === "string") return value.replace(/\{\{input:(image|video|audio|text|json)\}\}/g, (match, key) => replacements[key] ?? match);
    if (Array.isArray(value)) return value.map(item => replacePlaceholders(item, replacements));
    if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, replacePlaceholders(item, replacements)]));
    return value;
  }
  const WORKFLOW_STORE_KEY = "toonflow.comfyui.workflows.v1";
  const workflowStoreListeners = new Set();
  function readWorkflowStore() {
    try {
      const raw = globalThis.localStorage?.getItem(WORKFLOW_STORE_KEY);
      if (raw == null) return null;
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter(item => item && item.id && item.name && typeof item.workflowText === "string") : [];
    } catch { return null; }
  }
  function writeWorkflowStore(items, updatedId, allowCreate = false) {
    const combined = new Map((readWorkflowStore() ?? items).map(item => [item.id, item]));
    const updated = items.find(item => item.id === updatedId);
    // Only explicit add/save actions may create an ID absent from the shared library.
    if (updated && (allowCreate || combined.has(updatedId))) combined.set(updatedId, updated);
    const next = [...combined.values()];
    try {
      globalThis.localStorage?.setItem(WORKFLOW_STORE_KEY, JSON.stringify(next));
    } catch { /* storage may be unavailable */ }
    return next;
  }

  const declaredHandles = [
      { id: "in", type: "target", dataType: ["VIDEO", "IMAGE", "AUDIO", "STRING"], label: "图片、音频、视频、提示词输入" },
      { id: "image", type: "source", dataType: "IMAGE", label: "图片输出" },
      { id: "video", type: "source", dataType: "VIDEO", label: "视频输出" },
      { id: "audio", type: "source", dataType: "AUDIO", label: "音频输出" },
      { id: "data", type: "source", dataType: "STRING", label: "结果信息" }
  ];
  return defineComponent({
    name: "ComfyuiWorkflowNode",
    workflowCore: Core,
    inheritAttrs: false,
    handles: declaredHandles,
    setup(props) {
      const hostNode = typeof useNode === "function" ? useNode() : {};
      const hostFlow = typeof useVueFlow === "function" ? useVueFlow() : {};
      const workspaceFilesProvider = typeof Vue.inject === "function" ? Vue.inject("workspaceFiles", undefined) : undefined;
      let data = {};
      const resolveHost = () => unwrap(hostNode) || {};
      const resolveNodeId = () => {
        const host = resolveHost();
        const propNode = unwrap(props?.node);
        return unwrap(host?.id) || propNode?.id || unwrap(propNode?.id);
      };
      const resolveHostNode = () => {
        const host = resolveHost();
        const propNode = unwrap(props?.node);
        const nodeId = resolveNodeId();
        const found = nodeId && typeof hostFlow?.findNode === "function"
          ? unwrap(hostFlow.findNode(nodeId))
          : undefined;
        return found || unwrap(host?.node) || propNode;
      };
      data = unwrap(resolveHostNode()?.data) || unwrap(props?.data) || {};
      if (!data.outputs || typeof data.outputs !== "object") data.outputs = {};
      const baseUrl = ref(data.baseUrl || "http://127.0.0.1:8188");
      const workflowText = ref(typeof data.workflowText === "string" ? data.workflowText : '{\n  "3": {\n    "class_type": "KSampler",\n    "inputs": {}\n  }\n}');
      const status = ref("就绪");
      const promptId = ref("");
      const outputUrl = ref("");
      const outputEntriesRef = ref([]);
      const running = ref(false);
      const runProgress = ref({ stage: "", percent: null, detail: "" });
      let progressSocket;
      const closeProgressSocket = () => {
        const socket = progressSocket;
        progressSocket = undefined;
        if (socket) { socket.onmessage = null; socket.onclose = null; socket.onerror = null; socket.close(); }
      };
      const error = ref("");
      const fileInput = ref();
      const canvasInputs = computed(() => {
        const nodes = unwrap(hostFlow.getNodes) || [...(unwrap(hostFlow.nodeLookup)?.values?.() || [])];
        const edges = unwrap(hostFlow.getEdges) || [];
        return Core.collectCanvas(nodes, edges, resolveNodeId());
      });
      const management = ref(false);
      const workflowName = ref(typeof data.workflowName === "string" ? data.workflowName : "新工作流");
      const workflows = ref(readWorkflowStore() ?? (Array.isArray(data.workflows) ? data.workflows : []));
      const selectedWorkflow = ref(data.selectedWorkflow || "");
      const parameterDefs = ref(clone(Array.isArray(data.parameterDefs) ? data.parameterDefs : []));
      const advancedEditorOpen = ref(false);
      const preparedParameters = computed(() => {
        try { return Core.prepareParameters(parseWorkflow(workflowText.value), parameterDefs.value); }
        catch { return parameterDefs.value; }
      });
      const managedParameters = computed(() => Core.sortParameters(preparedParameters.value)
        .filter(item => item.tier !== "advanced" || advancedEditorOpen.value));
      const advancedParameterCount = computed(() => preparedParameters.value.filter(item => item.tier === "advanced").length);
      const visibleParameters = computed(() => preparedParameters.value.filter(item => item.visible !== false));
      const groupedVisibleParameters = computed(() => {
        const groups = new Map();
        visibleParameters.value.forEach((item, index) => {
          const key = item.groupKey || `other:${item.nodeId}`;
          const group = groups.get(key) || { key, label: item.groupLabel, category: item.category ?? 5,
            order: item.groupOrder ?? 0, index, items: [] };
          group.items.push({ item, index });
          groups.set(key, group);
        });
        return [...groups.values()].sort((a, b) => a.category - b.category ||
          a.order - b.order || a.index - b.index);
      });
      const parameterValues = ref(clone(data.parameterValues && typeof data.parameterValues === "object" ? data.parameterValues : {}));
      const canvasBindings = ref(clone(Array.isArray(data.canvasBindings) ? data.canvasBindings : []));
      const workflowOutputs = ref(clone(Array.isArray(data.workflowOutputs) ? data.workflowOutputs : []));
      const outputDefinitions = computed(() => {
        try {
          const w = parseWorkflow(workflowText.value);
          const found = new Map(Core.detectOutputs(w).map(item => [`${item.nodeId}:${item.kind}`, item]));
          for (const item of workflowOutputs.value) if (w[item.nodeId]?.class_type === item.classType)
            found.set(`${item.nodeId}:${item.kind}`, item);
          return [...found.values()];
        } catch { return []; }
      });
      const ignoredParameters = ref(data.ignoredParameters || []);
      const ignoredBindings = ref(data.ignoredBindings || []);
      const referenceMode = ref(data.referenceMode || "mentioned");
      const detecting = ref(false);
      const libraryConfirmation = ref(null);
      const confirmationElement = ref();
      let editorEpoch = 0;
      let infoCache = {}, infoUrl = "";
      let runEpoch = 0;
      const parameterEditorOpen = ref(false);
      const composerOpen = ref(data.composerOpen === true);
      const nodePrompt = ref(typeof data.nodePrompt === "string" ? data.nodePrompt : "");
      const previewUrls = ref({});
      const mentionQuery = ref(null);
      const mentionIndex = ref(0);
      const mentionItems = computed(() => {
        const query = (mentionQuery.value || "").toLowerCase();
        return canvasInputs.value.gallery.filter(r => `${r.alias} ${r.label}`.toLowerCase().includes(query));
      });
      const previewLeases = new Map();
      let editorElement, savedRange, mentionRange, composing = false, disposed = false;
      function persistPrompt() {
        data.nodePrompt = nodePrompt.value;
        data.composerOpen = composerOpen.value;
      }
      function toggleComposer() {
        composerOpen.value = !composerOpen.value;
        mentionQuery.value = null;
        persistPrompt();
        nextTick?.(() => hostFlow?.updateNodeInternals?.([resolveNodeId()]));
      }
      function safeMediaUrl(url) { return /^(?:https?:|data:(?:image|audio|video)\/|blob:)/i.test(url || "") ? url : ""; }
      function updatePreviews() {
        const gallery = composerOpen.value ? canvasInputs.value.gallery.filter(r => r.kind !== "audio") : [];
        const active = new Set(gallery.map(r => r.key));
        for (const [key, entry] of previewLeases) if (!active.has(key)) {
          entry.cancelled = true;
          entry.lease?.release?.();
          previewLeases.delete(key);
          const next = { ...previewUrls.value }; delete next[key]; previewUrls.value = next;
        }
        for (const r of gallery) {
          if (previewLeases.has(r.key)) continue;
          const entry = { cancelled: false, lease: undefined };
          previewLeases.set(r.key, entry);
          const direct = safeMediaUrl(r.url);
          if (direct) { previewUrls.value = { ...previewUrls.value, [r.key]: direct }; continue; }
          if (/^(?:[a-z][a-z0-9+.-]*:|[/\\])/i.test(r.url)) continue;
          const files = typeof workspaceFilesProvider === "function" ? workspaceFilesProvider() : undefined;
          if (typeof files?.acquireUrl !== "function") continue;
          Promise.resolve().then(async () => {
            const lease = await files.acquireUrl(r.url, r.mimeType);
            entry.lease = lease;
            if (entry.cancelled || disposed) { lease?.release?.(); return; }
            const url = safeMediaUrl(await lease.url);
            if (url && !entry.cancelled && !disposed) previewUrls.value = { ...previewUrls.value, [r.key]: url };
          }).catch(() => { /* A failed thumbnail must not prevent generation. */ });
        }
      }
      if (typeof watchEffect === "function") watchEffect(updatePreviews);
      if (typeof Vue.onUnmounted === "function") Vue.onUnmounted(() => {
        closeProgressSocket();
        disposed = true;
        for (const entry of previewLeases.values()) { entry.cancelled = true; entry.lease?.release?.(); }
        previewLeases.clear();
      });
      function serializePrompt(root) {
        let value = "";
        for (const child of root?.childNodes || []) {
          if (child.nodeType === 3) value += child.textContent.replace(/\u00a0/g, " ");
          else if (child.dataset?.refkey) value += Core.referenceToken(child.dataset.refkey);
          else if (child.nodeName === "BR") value += "\n";
          else {
            const block = /^(DIV|P)$/.test(child.nodeName);
            if (block && value && !value.endsWith("\n")) value += "\n";
            value += serializePrompt(child);
          }
        }
        return value;
      }
      function refreshChip(chip) {
        const r = canvasInputs.value.gallery.find(item => item.key === chip.dataset.refkey);
        chip.className = `comfyui-prompt-chip${r ? "" : " is-disconnected"}`;
        chip.title = r ? `${r.alias} · ${r.label}` : "参考素材已断开或已更换";
        chip.replaceChildren();
        if (r?.kind === "image" && previewUrls.value[r.key]) {
          const img = chip.ownerDocument.createElement("img");
          img.src = previewUrls.value[r.key]; img.alt = ""; img.draggable = false;
          chip.append(img);
        }
        const label = chip.ownerDocument.createElement("span");
        label.textContent = r?.alias || "已断开引用";
        chip.append(label);
      }
      function promptFragment(text) {
        const doc = editorElement.ownerDocument, fragment = doc.createDocumentFragment();
        for (const part of Core.promptSegments(text)) {
          if (part.key) {
            const chip = doc.createElement("span");
            chip.contentEditable = "false"; chip.dataset.refkey = part.key;
            refreshChip(chip); fragment.append(chip);
          } else part.text.split("\n").forEach((line, i) => {
            if (i) fragment.append(doc.createElement("br"));
            fragment.append(doc.createTextNode(line));
          });
        }
        return fragment;
      }
      function syncEditor() {
        if (!editorElement || composing) return;
        if (serializePrompt(editorElement) !== nodePrompt.value) editorElement.replaceChildren(promptFragment(nodePrompt.value));
        else editorElement.querySelectorAll("[data-refkey]").forEach(refreshChip);
        editorElement.dataset.empty = nodePrompt.value ? "false" : "true";
      }
      const setEditorElement = element => {
        if (element === editorElement) return;
        editorElement = element; savedRange = undefined;
        if (element) syncEditor();
      };
      if (typeof watchEffect === "function") watchEffect(() => {
        nodePrompt.value; canvasInputs.value.gallery; previewUrls.value;
        nextTick?.(syncEditor);
      });
      function rememberCaret() {
        const selection = editorElement?.ownerDocument.getSelection();
        if (selection?.rangeCount && editorElement.contains(selection.anchorNode) && editorElement.contains(selection.focusNode)) {
          savedRange = selection.getRangeAt(0).cloneRange();
          return savedRange;
        }
      }
      function updateMention() {
        if (composing) return;
        const range = rememberCaret();
        mentionRange = undefined; mentionQuery.value = null;
        if (!range || !range.collapsed || range.startContainer.nodeType !== 3) return;
        const before = range.startContainer.textContent.slice(0, range.startOffset);
        const match = before.match(/@([^@\s{}]*)$/);
        if (!match) return;
        mentionRange = range.cloneRange();
        mentionRange.setStart(range.startContainer, range.startOffset - match[0].length);
        mentionQuery.value = match[1]; mentionIndex.value = 0;
      }
      function onPromptInput() {
        if (composing) return;
        nodePrompt.value = serializePrompt(editorElement);
        persistPrompt();
        if (editorElement) editorElement.dataset.empty = nodePrompt.value ? "false" : "true";
        updateMention();
      }
      function insertPrompt(text, range = savedRange) {
        if (!editorElement || running.value) return;
        const doc = editorElement.ownerDocument;
        if (!range || !editorElement.contains(range.startContainer) || !editorElement.contains(range.endContainer)) {
          range = doc.createRange(); range.selectNodeContents(editorElement); range.collapse(false);
        }
        range.deleteContents();
        const fragment = promptFragment(text), last = fragment.lastChild;
        range.insertNode(fragment);
        if (last) { range.setStartAfter(last); range.collapse(true); }
        const selection = doc.getSelection(); selection.removeAllRanges(); selection.addRange(range);
        editorElement.focus(); savedRange = range.cloneRange();
        onPromptInput(); mentionQuery.value = null; mentionRange = undefined;
      }
      function insertReference(r) {
        insertPrompt(Core.referenceToken(r.key) + " ", mentionRange || savedRange);
      }
      function onPromptKeydown(event) {
        event.stopPropagation();
        if (composing || event.isComposing || mentionQuery.value === null) return;
        const items = mentionItems.value;
        if (event.key === "Escape") { event.preventDefault(); mentionQuery.value = null; mentionRange = undefined; }
        else if (items.length && ["ArrowDown", "ArrowUp"].includes(event.key)) {
          event.preventDefault();
          mentionIndex.value = (mentionIndex.value + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
          nextTick?.(() => editorElement?.parentElement.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" }));
        } else if (items.length && event.key === "Enter") {
          event.preventDefault(); insertReference(items[mentionIndex.value]);
        }
      }
      function onPromptPaste(event) {
        event.preventDefault(); event.stopPropagation();
        rememberCaret();
        insertPrompt(event.clipboardData?.getData("application/x-toonflow-prompt") || event.clipboardData?.getData("text/plain") || "");
      }
      function onPromptCopy(event) {
        const range = rememberCaret();
        if (!range || range.collapsed) return;
        event.preventDefault();
        const text = serializePrompt(range.cloneContents());
        event.clipboardData?.setData("application/x-toonflow-prompt", text);
        event.clipboardData?.setData("text/plain", Core.promptSegments(text).map(part => part.text ??
          `@${canvasInputs.value.gallery.find(r => r.key === part.key)?.alias || "已断开引用"}`).join(""));
        if (event.type === "cut" && !running.value) { range.deleteContents(); onPromptInput(); }
      }
      function useCanvasPrompt() {
        try { nodePrompt.value = Core.canvasPrompt(canvasInputs.value); persistPrompt(); nextTick?.(syncEditor); }
        catch (e) { error.value = e.message; }
      }
      const parameterIssues = computed(() => {
        let workflow;
        try { workflow = parseWorkflow(workflowText.value); } catch { return new Map(); }
        return new Map(parameterDefs.value.flatMap(item => {
          try {
            const value = Core.readInput(workflow, item.nodeId, item.path);
            if (Core.isLink(value, workflow)) throw new Error("参数指向连线，请改为上游常量字段");
            return [];
          } catch (e) { return [[item.key, e.message]]; }
        }));
      });

      const normalizedUrl = computed(() => `${window.location.origin}/api/localModels/comfy/get`);

      function persistNodeData() {
        data.baseUrl = baseUrl.value;
        data.workflowText = workflowText.value;
        data.workflowName = workflowName.value;
        data.workflows = workflows.value;
        data.selectedWorkflow = selectedWorkflow.value;
        data.parameterDefs = parameterDefs.value;
        data.parameterValues = parameterValues.value;
        data.canvasBindings = canvasBindings.value;
        data.workflowOutputs = workflowOutputs.value;
        data.ignoredParameters = ignoredParameters.value;
        data.ignoredBindings = ignoredBindings.value;
        data.referenceMode = referenceMode.value;
      }
      function resetWorkflowEditor() {
        ++editorEpoch;
        selectedWorkflow.value = "";
        workflowName.value = "";
        workflowText.value = "";
        parameterDefs.value = [];
        parameterValues.value = {};
        canvasBindings.value = [];
        workflowOutputs.value = [];
        advancedEditorOpen.value = false;
        ignoredParameters.value = [];
        ignoredBindings.value = [];
        referenceMode.value = "mentioned";
        infoCache = {}; infoUrl = "";
        error.value = "";
      }
      function refreshWorkflowLibrary() {
        const stored = readWorkflowStore();
        if (stored === null) return true;
        workflows.value = stored;
        const removed = selectedWorkflow.value && !stored.some(item => item.id === selectedWorkflow.value);
        if (removed) {
          resetWorkflowEditor();
          libraryConfirmation.value = null;
          status.value = "工作流已删除";
        }
        persistNodeData();
        return !removed;
      }
      workflowStoreListeners.add(refreshWorkflowLibrary);
      const onWorkflowStorage = event => {
        if (event.key === WORKFLOW_STORE_KEY) refreshWorkflowLibrary();
      };
      globalThis.addEventListener?.("storage", onWorkflowStorage);
      if (typeof Vue.onUnmounted === "function") Vue.onUnmounted(() => {
        workflowStoreListeners.delete(refreshWorkflowLibrary);
        globalThis.removeEventListener?.("storage", onWorkflowStorage);
      });
      refreshWorkflowLibrary();
      function persist(allowCreate = false) {
        if (!allowCreate && !refreshWorkflowLibrary()) return;
        if (selectedWorkflow.value) {
          workflows.value = workflows.value.map(item => item.id === selectedWorkflow.value
            ? {
                ...item,
                name: workflowName.value,
                baseUrl: baseUrl.value,
                workflowText: workflowText.value,
                parameterDefs: clone(parameterDefs.value),
                parameterValues: clone(parameterValues.value),
                canvasBindings: clone(canvasBindings.value),
                workflowOutputs: clone(workflowOutputs.value),
                ignoredParameters: [...ignoredParameters.value],
                ignoredBindings: [...ignoredBindings.value],
                referenceMode: referenceMode.value
              }
            : item);
        }
        workflows.value = writeWorkflowStore(workflows.value, selectedWorkflow.value, allowCreate);
        persistNodeData();
      }
      function selectWorkflow(item, allowCreate = false) {
        const stored = readWorkflowStore();
        const latest = stored?.find(entry => entry.id === item.id);
        if (stored !== null && !latest && !allowCreate) { refreshWorkflowLibrary(); return; }
        item = latest || item;
        workflows.value = stored ?? workflows.value;
        if (!workflows.value.some(entry => entry.id === item.id)) workflows.value = [...workflows.value, item];
        ++editorEpoch;
        selectedWorkflow.value = item.id;
        workflowName.value = item.name;
        baseUrl.value = item.baseUrl || baseUrl.value;
        workflowText.value = item.workflowText;
        parameterDefs.value = clone(Array.isArray(item.parameterDefs) ? item.parameterDefs : []);
        parameterValues.value = clone(item.parameterValues && typeof item.parameterValues === "object" ? item.parameterValues : {});
        canvasBindings.value = clone(item.canvasBindings || []);
        workflowOutputs.value = clone(item.workflowOutputs || []);
        advancedEditorOpen.value = false;
        ignoredParameters.value = [...(item.ignoredParameters || [])];
        ignoredBindings.value = [...(item.ignoredBindings || [])];
        referenceMode.value = item.referenceMode || "mentioned";
        persist(allowCreate);
      }
      function addWorkflow() {
        const item = { id: `workflow-${Date.now()}`, name: `新工作流 ${workflows.value.length + 1}`, baseUrl: baseUrl.value, workflowText: "{}", parameterDefs: [], parameterValues: {}, canvasBindings: [] };
        selectWorkflow(item, true);
      }
      function saveWorkflow() {
        if (!refreshWorkflowLibrary()) return;
        try { parseWorkflow(workflowText.value); } catch (e) { error.value = e.message; return; }
        const item = { id: selectedWorkflow.value || `workflow-${Date.now()}`, name: workflowName.value.trim() || "未命名工作流", baseUrl: baseUrl.value.trim() || "http://127.0.0.1:8188", workflowText: workflowText.value, parameterDefs: parameterDefs.value, parameterValues: parameterValues.value };
        const index = workflows.value.findIndex(entry => entry.id === item.id);
        workflows.value = index >= 0 ? workflows.value.map((entry, i) => i === index ? item : entry) : [...workflows.value, item];
        selectedWorkflow.value = item.id;
        persist(true); status.value = `已保存：${item.name}`;
      }
      function requestLibraryChange(item) {
        if (running.value || detecting.value) return;
        libraryConfirmation.value = item ? { id: item.id, name: item.name } : { clearAll: true };
        nextTick?.(() => confirmationElement.value?.focus());
      }
      function confirmLibraryChange() {
        const action = libraryConfirmation.value;
        if (!action || running.value || detecting.value) return;
        try {
          const stored = readWorkflowStore() ?? workflows.value;
          const next = action.clearAll ? [] : stored.filter(item => item.id !== action.id);
          if (!globalThis.localStorage?.setItem) throw new Error("工作流存储不可用，未执行删除");
          globalThis.localStorage.setItem(WORKFLOW_STORE_KEY, JSON.stringify(next));
          workflows.value = next;
          if (action.clearAll || selectedWorkflow.value === action.id) resetWorkflowEditor();
          persistNodeData();
          libraryConfirmation.value = null;
          for (const refresh of workflowStoreListeners) refresh();
          error.value = "";
          status.value = action.clearAll ? "已清除所有工作流和参数" : `已删除：${action.name}`;
        } catch (e) {
          error.value = `删除失败：${e.message}`;
        }
      }
      function addParameter() {
        let number = 1;
        while (parameterDefs.value.some(item => item.key === `param${number}`)) number++;
        parameterDefs.value = [...parameterDefs.value, {
          key: `param${number}`,
          label: "新参数",
          type: "text",
          nodeId: "",
          path: "",
          defaultValue: "",
          visible: true
        }];
        persist();
      }
      function updateParameter(index, key, value) {
        parameterDefs.value = parameterDefs.value.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item);
        persist();
      }
      function setAllParametersVisible(visible) {
        const keys = new Set(managedParameters.value.map(item => item.key));
        parameterDefs.value = parameterDefs.value.map(item => keys.has(item.key) ? { ...item, visible } : item);
        persist();
      }
      async function loadInfo(workflow, includeLoaders = false, refresh = false) {
        const url = normalizedUrl.value;
        if (infoUrl !== url || refresh) { infoCache = {}; infoUrl = url; }
        const types = [...new Set([...Object.values(workflow).map(n => n.class_type),
          ...(includeLoaders ? ["LoadImage", "LoadAudio", "LoadAudioUI", "LoadVideoUI", "VHS_LoadVideo"] : [])])];
        try { await fetchJson(`${url}/system_stats`, {}, 3500); }
        catch { return { infos: { ...infoCache }, missing: types.filter(type => !infoCache[type]) }; }
        const missing = [];
        // Limit parallel lookups so large workflows do not overwhelm the local server.
        for (let i = 0; i < types.length; i += 6) await Promise.all(types.slice(i, i + 6).map(async type => {
          if (infoCache[type]) return;
          try {
            const result = await fetchJson(`${url}/object_info/${encodeURIComponent(type)}`);
            if (result[type]) infoCache[type] = result[type]; else missing.push(type);
          } catch { missing.push(type); }
        }));
        return { infos: { ...infoCache }, missing };
      }
      async function detectParameters(includeAdvanced = false) {
        if (detecting.value || running.value) return;
        detecting.value = true; error.value = ""; status.value = "检测中...";
        const text = workflowText.value, id = selectedWorkflow.value, url = normalizedUrl.value;
        try {
          const workflow = parseWorkflow(text);
          const { infos, missing } = await loadInfo(workflow, false, true);
          if (text !== workflowText.value || id !== selectedWorkflow.value || url !== normalizedUrl.value) throw new Error("工作流或地址已变化，请重新检测");
          const filled = Core.fillRequiredDefaults(workflow, infos);
          let modelUpdates = [], modelWarning = "";
          try { modelUpdates = Core.resolveModelFiles(workflow, infos, modelFileReplacements); }
          catch (e) { modelWarning = e.message; }
          const found = Core.detect(workflow, infos, { includeAdvanced });
          const before = parameterDefs.value.length;
          parameterDefs.value = Core.mergeDetection(Core.prepareParameters(workflow, parameterDefs.value),
            found.parameters, ignoredParameters.value);
          canvasBindings.value = Core.normalizeH3Bindings(workflow,
            Core.mergeDetection(canvasBindings.value, found.bindings, ignoredBindings.value, Core.bindingId), infos);
          refreshModelChoices(workflow, infos);
          applyModelUpdates(modelUpdates);
          workflowOutputs.value = found.outputs;
          if (includeAdvanced) advancedEditorOpen.value = true;
          if (filled.length || modelUpdates.length) workflowText.value = JSON.stringify(workflow, null, 2);
          persist();
          status.value = `检测完成：新增 ${parameterDefs.value.length - before} 项${includeAdvanced ? "参数" : "主要参数"}，${canvasBindings.value.length} 个输入入口，${found.outputs.length} 个输出节点${filled.length ? `；补全 ${filled.length} 个必填输入` : ""}${modelUpdates.length ? `；修复 ${modelUpdates.length} 个模型文件路径` : ""}${missing.length ? "；部分节点离线，仅按 JSON 检测" : ""}`;
          if (modelWarning) error.value = modelWarning;
        } catch (e) { error.value = e.message; status.value = "检测失败"; }
        finally { detecting.value = false; }
      }
      function updateBinding(index, key, value) {
        canvasBindings.value = canvasBindings.value.map((b, i) => i === index ? { ...b, [key]: value } : b);
        persist();
      }
      function removeBinding(index) {
        const b = canvasBindings.value[index];
        ignoredBindings.value = [...new Set([...ignoredBindings.value, Core.bindingId(b)])];
        canvasBindings.value = canvasBindings.value.filter((_, i) => i !== index);
        persist();
      }
      function resetDetection() {
        ignoredParameters.value = []; ignoredBindings.value = [];
        return detectParameters();
      }
      async function uploadReference(r) {
        const controller = new AbortController();
        let timer;
        let blob;
        try {
          const read = async () => {
            if (/^(?:https?:|data:|blob:)/i.test(r.url)) {
              const response = await fetch(r.url, { signal: controller.signal });
              if (!response.ok) throw new Error(`${r.label} 读取失败：${response.status}`);
              return response.blob();
            }
            if (/^(?:[a-z][a-z0-9+.-]*:|[/\\])/i.test(r.url)) throw new Error(`${r.label} 不是可读取的工作区文件或媒体地址`);
            const files = typeof workspaceFilesProvider === "function" ? workspaceFilesProvider() : undefined;
            if (typeof files?.read !== "function") throw new Error("当前画布未提供工作区文件读取能力，请重新打开画布");
            const bytes = await files.read(r.url);
            return new Blob([bytes], { type: r.mimeType || "" });
          };
          blob = await Promise.race([read(), new Promise((_, reject) => {
            timer = setTimeout(() => { controller.abort(); reject(new Error(`${r.label} 读取超时`)); }, 60000);
          })]);
        } finally { clearTimeout(timer); }
        const ext = ({ "image/jpeg": "jpg", "image/webp": "webp", "image/png": "png", "audio/mpeg": "mp3",
          "audio/flac": "flac", "audio/ogg": "ogg", "audio/wav": "wav", "video/mp4": "mp4", "video/webm": "webm" })[blob.type || r.mimeType] ||
          (r.kind === "image" ? "png" : r.kind === "audio" ? "wav" : "mp4");
        const form = new FormData();
        form.append("image", blob, `toonflow-${r.kind}-${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`);
        const file = await fetchJson(`${normalizedUrl.value}/upload/image`, { method: "POST", body: form });
        if (!file.name) throw new Error(`${r.label} 上传未返回文件名`);
        return [file.subfolder, file.name].filter(Boolean).join("/");
      }
      function refreshModelChoices(workflow, infos) {
        const detected = new Map(Core.detect(workflow, infos, { includeAdvanced: true }).parameters
          .filter(p => Core.modelField(p.path)).map(p => [`${p.nodeId}:${p.path}`, p]));
        parameterDefs.value = parameterDefs.value.map(p => {
          const latest = detected.get(`${p.nodeId}:${p.path}`);
          return latest?.options ? { ...p, type: "enum", options: latest.options, detectedType: "enum" } : p;
        });
      }
      function applyModelUpdates(updates) {
        parameterDefs.value = parameterDefs.value.map(p => {
          const update = updates.find(item => item.nodeId === p.nodeId && item.path === p.path);
          if (!update) return p;
          if (parameterValues.value[p.key] === update.previous)
            parameterValues.value = { ...parameterValues.value, [p.key]: update.value };
          return p.defaultValue === update.previous ? { ...p, defaultValue: update.value } : p;
        });
      }
      async function connectProgress(url, clientId, epoch) {
        closeProgressSocket();
        if (url.includes("/api/localModels/comfy/")) return;
        if (typeof WebSocket !== "function") return;
        const socketUrl = new URL(`${url}/ws`);
        socketUrl.protocol = socketUrl.protocol === "https:" ? "wss:" : "ws:";
        socketUrl.searchParams.set("clientId", clientId);
        let socket, activePrompt = "";
        const early = [];
        function accept(message) {
          if (epoch !== runEpoch || !running.value || !message?.data?.prompt_id ||
              message.data.prompt_id !== activePrompt) return;
          const d = message.data;
          if (message.type === "execution_start") runProgress.value = { stage: "正在运行", percent: null, detail: "加载模型与准备素材" };
          if (message.type === "executing") runProgress.value = { stage: d.node ? "正在运行" : "整理输出", percent: null,
            detail: d.node ? `节点 ${d.node}` : "等待输出文件" };
          const entries = message.type === "progress_state" ? Object.values(d.nodes || {}).filter(n => n.state === "running") :
            message.type === "progress" ? [d] : [];
          const p = entries.find(n => Number.isFinite(n.value) && Number.isFinite(n.max) && n.max > 0);
          if (p) runProgress.value = { stage: "当前步骤进度", percent: Math.min(100, Math.max(0, Math.round(p.value / p.max * 100))),
            detail: `节点 ${p.node_id || p.node || d.node || ""} · ${p.value} / ${p.max}` };
          if (["execution_success", "execution_error", "execution_interrupted"].includes(message.type))
            runProgress.value = { stage: message.type === "execution_success" ? "整理输出" : "等待任务状态", percent: null, detail: "" };
        }
        try {
          socket = new WebSocket(socketUrl.toString());
          progressSocket = socket;
          socket.onmessage = event => {
            if (typeof event.data !== "string") return;
            try {
              const message = JSON.parse(event.data);
              if (!activePrompt) { if (early.length < 200) early.push(message); }
              else accept(message);
            } catch { /* Binary previews and malformed messages do not affect history polling. */ }
          };
          const disconnected = () => {
            if (epoch === runEpoch && running.value && progressSocket === socket)
              runProgress.value = { stage: "正在运行", percent: null, detail: "等待任务结果" };
          };
          await new Promise(resolve => {
            const timer = setTimeout(resolve, 2000);
            const ready = () => { clearTimeout(timer); resolve(); };
            socket.onopen = ready;
            socket.onerror = () => { disconnected(); ready(); };
            socket.onclose = () => { disconnected(); ready(); };
          });
        } catch { return; }
        return id => { activePrompt = id; early.forEach(accept); early.length = 0; };
      }
      async function run() {
        if (running.value) return;
        if (editorElement && !composing) onPromptInput();
        const epoch = ++runEpoch;
        let submitting = false;
        closeProgressSocket();
        runProgress.value = { stage: "预检", percent: null, detail: "检查工作流与模型文件" };
        running.value = true; error.value = ""; promptId.value = ""; outputUrl.value = ""; outputEntriesRef.value = []; status.value = "提交中...";
        for (const kind of ["image", "video", "audio", "comfyui", "data"]) delete data.outputs[kind];
        persist();
        const defs = clone(preparedParameters.value), values = clone(parameterValues.value);
        let bindings = clone(canvasBindings.value);
        const workflowSource = workflowText.value, workflowKey = selectedWorkflow.value, bindingSnapshot = JSON.stringify(bindings);
        let persistedSource = workflowSource;
        const prompt = nodePrompt.value;
        try {
          let workflow = parseWorkflow(workflowSource);
          const canvas = canvasInputs.value;
          status.value = "工作流预检中...";
          const { infos, missing } = await loadInfo(workflow,
            Boolean(canvas.direct.length || prompt.trim() || Core.isH3ReferenceWorkflow(workflow)), true);
          if (epoch !== runEpoch) return;
          const missingTypes = missing.filter(type => Object.values(workflow).some(n => n.class_type === type));
          if (missingTypes.length) throw new Error(`无法读取本地节点定义，工作流未提交：${missingTypes.join("、")}；请检查 ComfyUI 连接和自定义节点安装`);
          Core.fillRequiredDefaults(workflow, infos);
          if (workflowSource === workflowText.value && workflowKey === selectedWorkflow.value) {
            refreshModelChoices(workflow, infos);
            persist();
          }
          Core.applyParameters(workflow, defs, values, infos);
          const modelUpdates = Core.resolveModelFiles(workflow, infos, modelFileReplacements);
          if (modelUpdates.length && workflowSource === workflowText.value && workflowKey === selectedWorkflow.value &&
              JSON.stringify(parameterValues.value) === JSON.stringify(values)) {
            const savedWorkflow = parseWorkflow(workflowSource);
            for (const update of modelUpdates) Core.writeInput(savedWorkflow, update.nodeId, update.path, update.value);
            workflowText.value = JSON.stringify(savedWorkflow, null, 2);
            persistedSource = workflowText.value;
            applyModelUpdates(modelUpdates);
            persist();
          }
          if (canvas.direct.length || prompt.trim() || Core.isH3ReferenceWorkflow(workflow, infos)) {
            bindings = Core.normalizeH3Bindings(workflow, bindings, infos);
            const selection = Core.selectReferences(canvas, referenceMode.value, prompt);
            Core.validateBindings(workflow, bindings, selection);
            // Validate graph rewrites before uploading any files.
            const dryUploads = Object.fromEntries(selection.selected.map(r => [r.key, "toonflow-preflight"]));
            const dryWorkflow = Core.applyCanvas(clone(workflow), bindings, selection, dryUploads, infos);
            Core.fillRequiredDefaults(dryWorkflow, infos);
            Core.validateRequiredInputs(dryWorkflow, infos);
            if (JSON.stringify(bindings) !== bindingSnapshot && persistedSource === workflowText.value &&
                workflowKey === selectedWorkflow.value && JSON.stringify(canvasBindings.value) === bindingSnapshot) {
              canvasBindings.value = clone(bindings);
              persist();
            }
            const uploads = {};
            for (const r of selection.selected) {
              if (epoch !== runEpoch) return;
              status.value = `上传 ${Core.names[r.kind]} ${r.index}...`;
              runProgress.value = { stage: "上传参考素材", percent: null, detail: `${Core.names[r.kind]} ${r.index} / ${selection.counts[r.kind]}` };
              uploads[r.key] = await uploadReference(r);
            }
            workflow = Core.applyCanvas(workflow, bindings, selection, uploads, infos);
            const replacements = { text: Core.renderPrompt(workflow, selection, infos) };
            for (const r of selection.selected) replacements[r.kind] ??= uploads[r.key];
            workflow = replacePlaceholders(workflow, replacements);
          }
          Core.fillRequiredDefaults(workflow, infos);
          Core.validateRequiredInputs(workflow, infos);
          if (epoch !== runEpoch) return;
          status.value = "提交中...";
          runProgress.value = { stage: "提交任务", percent: null, detail: "" };
          const clientId = `toonflow-${Date.now()}-${Math.random().toString(36).slice(2)}`;
          const trackPrompt = await connectProgress(normalizedUrl.value, clientId, epoch);
          if (epoch !== runEpoch) return;
          submitting = true;
          const result = await fetchJson(`${normalizedUrl.value}/prompt`, {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt: workflow, client_id: clientId })
          });
          submitting = false;
          promptId.value = result.prompt_id || "";
          const validationError = Core.formatNodeErrors(result.node_errors);
          if (validationError) throw new Error(`工作流校验失败${promptId.value ? "（部分分支已入队，勿重复提交）" : ""}：\n${validationError}`);
          if (!promptId.value) throw new Error(result.error?.message || "ComfyUI 未返回 prompt_id");
          runProgress.value = { stage: "等待运行", percent: null, detail: "任务已提交" };
          trackPrompt?.(promptId.value);
          status.value = `运行中 ${promptId.value}`;
          for (let i = 0; i < 1800 && epoch === runEpoch; i += 1) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            if (epoch !== runEpoch) return;
            const history = await fetchJson(`${normalizedUrl.value}/history/${encodeURIComponent(promptId.value)}`);
            if (epoch !== runEpoch) return;
            const item = history[promptId.value];
            if (!item) continue;
            if (["error", "failed"].includes(item.status?.status_str)) throw new Error(item.status.messages?.map(m => JSON.stringify(m)).join("\n") || "工作流执行失败");
            const entries = outputEntries(item);
            if (entries.length && (item.status?.completed || item.status?.status_str === "success")) {
              outputEntriesRef.value = entries;
              const image = entries.find(entry => entry.kind === "images" || entry.kind === "gifs" || entry.kind === "videos") || entries[0];
              const query = new URLSearchParams({ filename: image.filename, subfolder: image.subfolder || "", type: image.type || "output" });
              outputUrl.value = `${normalizedUrl.value}/view?${query.toString()}`;
              data.outputs = data.outputs || {};
              for (const kind of ["image", "video", "audio"]) delete data.outputs[kind];
              for (const entry of entries) {
                const kind = /\.(mp4|webm|mov)$/i.test(entry.filename || "") ? "video" :
                  entry.kind === "audio" || /\.(wav|mp3|flac|ogg|m4a)$/i.test(entry.filename || "") ? "audio" : "image";
                const query = new URLSearchParams({ filename: entry.filename, subfolder: entry.subfolder || "", type: entry.type || "output" });
                if (!data.outputs[kind]) data.outputs[kind] = { dataType: kind.toUpperCase(),
                  value: { url: `${normalizedUrl.value}/view?${query}`, mimeType: kind === "video" ? "video/mp4" : kind === "audio" ? "audio/wav" : "image/png" } };
              }
              data.outputs.comfyui = { dataType: "JSON", value: { promptId: promptId.value, outputs: entries } };
              data.outputs.data = { dataType: "STRING", value: JSON.stringify({ promptId: promptId.value, outputs: entries }) };
              status.value = "完成";
              runProgress.value = { stage: "完成", percent: 100, detail: "" };
              break;
            }
            if (item.status?.completed || item.status?.status_str === "success") {
              throw new Error("任务已结束，但未产生图片、视频或音频输出；请检查工作流的保存/输出节点及 ComfyUI 校验记录。");
            }
          }
          if (status.value.startsWith("运行中")) status.value = "等待超时，请检查 ComfyUI";
        } catch (e) {
          const message = e instanceof Error ? e.message : String(e);
          const uncertain = submitting && !e.httpStatus;
          error.value = uncertain ? `提交结果未确认，请先检查 ComfyUI 队列或历史，避免重复运行：${message}` : message;
          status.value = uncertain ? "提交未确认" : "失败";
        }
        finally { if (epoch === runEpoch) { running.value = false; closeProgressSocket(); } }
      }
      async function testConnection() {
        error.value = ""; status.value = "连接测试中...";
        try { await fetchJson(`${normalizedUrl.value}/system_stats`); status.value = "ComfyUI 连接正常"; }
        catch (e) { error.value = e instanceof Error ? e.message : String(e); status.value = "连接失败"; }
      }
      function importWorkflow(event) {
        const file = event.target.files?.[0]; event.target.value = "";
        if (!file) return;
        const epoch = editorEpoch;
        const reader = new FileReader();
        reader.onload = () => {
          if (epoch !== editorEpoch) return;
          try {
            const api = parseWorkflow(String(reader.result || ""));
            workflowText.value = JSON.stringify(api, null, 2); workflowOutputs.value = [];
            persist(); status.value = `已导入 ${file.name}`; error.value = "";
          } catch (e) { error.value = e instanceof Error ? e.message : "JSON 文件解析失败"; status.value = "导入失败"; }
        };
        reader.readAsText(file);
      }
      async function stop() {
        if (!running.value) return;
        // Keep the run locked until the global ComfyUI interrupt request completes.
        try { await fetchJson(`${normalizedUrl.value}/interrupt`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt_id: promptId.value }) }); ++runEpoch; status.value = "已请求中断"; running.value = false; closeProgressSocket(); }
        catch (e) { error.value = `中断未确认：${e.message}`; }
      }

      const field = (label, child) => h("div", { style: { marginBottom: "12px" } }, [h("div", { style: { fontWeight: "600", marginBottom: "6px" } }, label), child]);
      const controlStyle = { width: "100%", minWidth: "0", boxSizing: "border-box", padding: "7px 8px",
        border: "1px solid var(--el-border-color)", borderRadius: "5px", color: "inherit", background: "var(--el-bg-color)", fontSize: "12px" };
      const textInput = (value, onInput, placeholder = "", extra = {}) => h("input", { value: value ?? "", class: "nodrag", placeholder,
        ...extra, style: { ...controlStyle, ...(extra.style || {}) }, onInput });
      const selectInput = (value, entries, onChange, extra = {}) => h("select", { value, class: "nodrag", ...extra, style: controlStyle, onChange },
        entries.map(([v, label]) => h("option", { value: v }, label)));
      const smallButton = (label, onClick, extra = {}) => h(ElementPlus.ElButton, { size: "small", onClick, ...extra }, () => label);
      // Stop canvas gestures without cancelling native scrollbar and form-control behavior.
      const stopCanvasGesture = event => event.stopPropagation();
      const scrollProps = { class: "nodrag nopan nowheel comfyui-scroll", onPointerdown: stopCanvasGesture,
        onMousedown: stopCanvasGesture, onTouchstart: stopCanvasGesture, onWheel: stopCanvasGesture };
      const scrollStyle = { overflow: "auto", scrollbarGutter: "stable", overscrollBehavior: "contain" };
      const visibilityCheckboxStyle = { width: "16px", height: "16px", margin: "0", cursor: "pointer",
        accentColor: "var(--el-color-primary)" };
      const libraryConfirmationPanel = () => libraryConfirmation.value ? h("section", {
        ref: confirmationElement, role: "alertdialog", tabindex: -1,
        "aria-label": libraryConfirmation.value.clearAll ? "清除所有工作流和参数" : "删除工作流",
        class: "nodrag nopan", onKeydown: e => {
          if (e.key === "Escape") { e.stopPropagation(); libraryConfirmation.value = null; }
        },
        style: { marginTop: "10px", padding: "12px", border: "1px solid var(--el-color-danger)",
          borderRadius: "5px", background: "var(--el-color-danger-light-9)", overflowWrap: "anywhere" }
      }, [
        h("strong", {}, libraryConfirmation.value.clearAll ? "清除所有工作流和参数？" : `删除“${libraryConfirmation.value.name}”？`),
        h("p", { style: { margin: "8px 0", lineHeight: "1.6" } }, libraryConfirmation.value.clearAll
          ? "将清空全部已保存工作流及当前节点的 JSON、参数和输入绑定。此操作不可撤销。"
          : "此工作流将从共享列表中删除，使用它的节点将重置工作流配置。"),
        h("div", { style: { display: "flex", justifyContent: "flex-end", flexWrap: "wrap", gap: "8px" } }, [
          smallButton("取消", () => { libraryConfirmation.value = null; }),
          smallButton(libraryConfirmation.value.clearAll ? "确认清除" : "确认删除", confirmLibraryChange,
            { type: "danger", disabled: running.value || detecting.value })
        ])
      ]) : null;
      function valueControl(item, value, update) {
        if (item.type === "boolean") return h("input", { type: "checkbox", class: "nodrag", checked: value === true,
          "aria-label": item.label, onChange: e => update(e.target.checked) });
        if (item.type === "enum" && item.options?.length) return selectInput(value,
          [...(!item.options.includes(value) ? [[value, `未安装：${value}`]] : []), ...item.options.map(v => [v, String(v)])],
          e => update(item.options.find(v => String(v) === e.target.value)), { "aria-label": item.label });
        return textInput(value, e => update(e.target.value), "", { "aria-label": item.label,
          ...(item.type === "number" ? { type: "number", min: item.min, max: item.max, step: item.step || "any", inputMode: "decimal" } : {}) });
      }
      const rowStyle = { display: "grid", gridTemplateColumns: "minmax(120px,1.2fr) 66px minmax(105px,1fr) 76px minmax(110px,1fr) 56px",
        gap: "6px", alignItems: "center", padding: "5px 0", minWidth: "640px" };
      const sectionHeading = (label, controls = []) => h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "8px" } },
        [h("strong", {}, label), h("div", { style: { display: "flex", gap: "6px" } }, controls)]);
      function parameterDefinitionRows() {
        const groups = new Map();
        for (const item of managedParameters.value) {
          const key = item.tier === "advanced" ? "advanced" :
            item.groupKey?.startsWith("model:") ? "model" : item.groupKey?.startsWith("other:") ? "custom" : item.groupKey || "custom";
          const group = groups.get(key) || { key, label: key === "advanced" ? "高级参数" :
            key === "custom" ? "自定义设置" : item.groupLabel || "其它参数", items: [] };
          group.items.push(item); groups.set(key, group);
        }
        return [...groups.values()].flatMap(group => [
          h("div", { "data-definition-group": group.key,
            style: { padding: "10px 0 4px", fontSize: "12px", fontWeight: "600", minWidth: "640px" } }, group.label),
          ...group.items.map(item => {
            const index = parameterDefs.value.findIndex(p => p.key === item.key);
            return h("div", { key: item.key,
              style: { ...rowStyle, ...(parameterIssues.value.has(item.key) ? { background: "var(--el-color-danger-light-9)" } : {}) },
              title: parameterIssues.value.get(item.key) || item.sourceLabel, "data-invalid": parameterIssues.value.has(item.key) || undefined }, [
              textInput(item.label, e => updateParameter(index, "label", e.target.value), "名称"),
              textInput(item.nodeId, e => updateParameter(index, "nodeId", e.target.value), "ID"),
              textInput(item.path, e => updateParameter(index, "path", e.target.value), "字段"),
              selectInput(item.type || "text", [["text", "文本"], ["number", "数字"], ["boolean", "开关"], ["enum", "选项"]],
                e => updateParameter(index, "type", e.target.value)),
              valueControl(item, item.defaultValue, v => updateParameter(index, "defaultValue", v)),
              h("input", { type: "checkbox", class: "nodrag comfyui-param-visibility", checked: item.visible !== false,
                style: { ...visibilityCheckboxStyle, justifySelf: "center" }, title: "在主界面显示此参数",
                "aria-label": `显示参数 ${item.label || item.key}`, onChange: e => updateParameter(index, "visible", e.target.checked) })
            ]);
          })
        ]);
      }
      const parameterDefinitionEditor = () => h("section", { style: { marginTop: "12px", borderTop: "1px solid var(--el-border-color-lighter)", paddingTop: "12px" } }, [
        sectionHeading(`主要参数 · ${preparedParameters.value.length - advancedParameterCount.value}`, [smallButton("+", addParameter, { title: "添加参数", "aria-label": "添加参数" })]),
        h("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px", marginBottom: "8px" } }, [
          smallButton("提取高级参数", () => detectParameters(true), { text: true, disabled: detecting.value || running.value }),
          advancedParameterCount.value ? smallButton(advancedEditorOpen.value ? "收起高级参数" : "展开高级参数",
            () => { advancedEditorOpen.value = !advancedEditorOpen.value; }, { text: true, "aria-expanded": advancedEditorOpen.value }) : null,
          advancedParameterCount.value ? h("span", { style: { fontSize: "11px", color: "var(--el-text-color-secondary)" } }, `${advancedParameterCount.value} 项高级参数`) : null
        ]),
        parameterIssues.value.size ? h("div", { role: "alert", style: { color: "var(--el-color-danger)", fontSize: "12px", marginBottom: "6px" } },
          `${parameterIssues.value.size} 项参数绑定无效`) : null,
        h("div", { ...scrollProps, class: `${scrollProps.class} comfyui-parameter-definition-list`,
          style: { ...scrollStyle, maxHeight: "280px" } }, [
          h("div", { style: { ...rowStyle, color: "var(--el-text-color-secondary)", fontSize: "11px",
            position: "sticky", top: "0", zIndex: "1", background: "var(--el-bg-color)" } }, [
            ...["名称", "节点 ID", "inputs 字段", "类型", "默认值"].map(t => h("span", {}, t)),
            h("label", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "4px", cursor: "pointer", whiteSpace: "nowrap" } }, [
              h("input", { type: "checkbox", class: "nodrag", "aria-label": "全选自定义参数", title: "全选 / 取消全选",
                style: visibilityCheckboxStyle, disabled: !managedParameters.value.length,
                checked: managedParameters.value.length > 0 && managedParameters.value.every(item => item.visible !== false),
                indeterminate: managedParameters.value.some(item => item.visible !== false) && managedParameters.value.some(item => item.visible === false),
                onChange: e => setAllParametersVisible(e.target.checked) }),
              h("span", {}, "全选")
            ])
          ]),
          ...parameterDefinitionRows()
        ])
      ]);
      function bindingRows() {
        return ["text", "image", "audio", "video"].flatMap(kind => {
          const items = canvasBindings.value.map((b, i) => ({ b, i })).filter(({ b }) => b.kind === kind);
          if (!items.length) return [];
          return [
            h("div", { style: { padding: "8px 0 4px", fontSize: "12px", fontWeight: "600" } }, `${Core.names[kind]}输入`),
            ...items.map(({ b, i }) => h("div", {
              style: { display: "grid", gridTemplateColumns: "22px 76px 66px minmax(120px,1fr) 78px 28px", gap: "6px", alignItems: "center", padding: "4px 0", minWidth: "540px" }, title: b.label
            }, [
              h("input", { type: "checkbox", checked: b.enabled !== false, title: "启用绑定", onChange: e => updateBinding(i, "enabled", e.target.checked) }),
              selectInput(b.kind, Object.entries(Core.names), e => updateBinding(i, "kind", e.target.value)),
              textInput(b.nodeId, e => updateBinding(i, "nodeId", e.target.value), "节点 ID"),
              textInput(b.path, e => updateBinding(i, "path", e.target.value), "inputs 字段"),
              b.mode === "slots" ? textInput(b.max, e => updateBinding(i, "max", e.target.value), "上限", { type: "number", min: 0, max: b.capacity, title: `最多 ${b.capacity} 个` }) : h("span", { style: { color: "var(--el-text-color-secondary)", fontSize: "11px" } }, b.kind === "text" ? "提示词" : "文件入口"),
              smallButton("×", () => removeBinding(i), { text: true, type: "danger", title: "删除绑定", "aria-label": "删除绑定" })
            ]))
          ];
        });
      }
      const bindingEditor = () => h("section", { style: { margin: "12px 0", paddingTop: "12px", borderTop: "1px solid var(--el-border-color-lighter)" } }, [
        sectionHeading(`输入入口 · ${canvasBindings.value.length}`, [
          selectInput(referenceMode.value, [["mentioned", "文字参考"], ["all", "全部连线"]], e => { referenceMode.value = e.target.value; persist(); }),
          smallButton("+", () => { canvasBindings.value = [...canvasBindings.value, { kind: "text", mode: "file", nodeId: "", path: "", enabled: true }]; persist(); },
            { title: "添加画布绑定", "aria-label": "添加画布绑定" })
        ]),
        h("div", { ...scrollProps, style: { ...scrollStyle, maxHeight: "220px" } }, bindingRows())
      ]);
      const outputDefinitionPanel = () => h("section", { style: { margin: "12px 0", paddingTop: "12px", borderTop: "1px solid var(--el-border-color-lighter)" } }, [
        sectionHeading(`输出节点 · ${outputDefinitions.value.length}`),
        outputDefinitions.value.length ? h("div", { ...scrollProps, style: { ...scrollStyle, maxHeight: "160px" } },
          outputDefinitions.value.map(item => h("div", { key: `${item.nodeId}:${item.kind}`, "data-output-node": item.nodeId,
            style: { display: "grid", gridTemplateColumns: "76px 66px minmax(0,1fr)", gap: "8px", padding: "5px 0", fontSize: "12px" } }, [
            h("span", {}, `${Core.names[item.kind]}${item.preview ? "预览" : "输出"}`),
            h("span", {}, `ID ${item.nodeId}`),
            h("span", { style: { overflowWrap: "anywhere" } }, item.label)
          ]))) : h("span", { style: { color: "var(--el-text-color-secondary)", fontSize: "12px" } }, "未识别到媒体输出节点")
      ]);
      const parameterValue = item => h("div", { key: item.key, "data-parameter-key": item.key,
        style: { minWidth: "0" }, title: `${item.sourceLabel || ""} · ${item.nodeId}.${item.path}` }, [
        h("label", { style: { display: "block", marginBottom: "5px", fontSize: "12px", overflowWrap: "anywhere" } }, item.label || item.key),
        valueControl(item, parameterValues.value[item.key] ?? item.defaultValue ?? "", v => {
          parameterValues.value = { ...parameterValues.value, [item.key]: v }; persist();
        })
      ]);
      const parameterEditor = () => !visibleParameters.value.length ? null : h("section", { class: "nodrag nopan comfyui-parameters", onClick: e => e.stopPropagation(),
        style: { marginTop: "12px", paddingTop: "12px", borderTop: "1px solid var(--el-border-color-light)" } }, [
          sectionHeading(`工作流参数 · ${visibleParameters.value.length}`, [smallButton(parameterEditorOpen.value ? "收起参数" : "展开参数",
            () => { parameterEditorOpen.value = !parameterEditorOpen.value; nextTick?.(() => hostFlow?.updateNodeInternals?.([resolveNodeId()])); },
            { text: true, "aria-expanded": parameterEditorOpen.value })]),
          !parameterEditorOpen.value ? null : h("div", { ...scrollProps, class: `${scrollProps.class} comfyui-parameter-values`,
            style: { ...scrollStyle, maxHeight: "480px" } }, groupedVisibleParameters.value.map(group =>
              h("section", { key: group.key, "data-parameter-group": group.key,
                style: { display: "grid", gridTemplateColumns: group.key.startsWith("model:") ? "minmax(0,1fr)" : "repeat(2,minmax(0,1fr))",
                  gap: "10px", marginBottom: "10px" } }, [
                group.category > 1 && group.label ? h("strong", { style: { gridColumn: "1 / -1", fontSize: "12px" } }, group.label) : null,
                ...group.items.sort((a, b) => (a.item.order ?? 0) - (b.item.order ?? 0) ||
                  String(a.item.nodeId).localeCompare(String(b.item.nodeId), undefined, { numeric: true }) || a.index - b.index)
                  .map(({ item }) => parameterValue(item))
              ])))
        ]);
      const referenceCounts = () => {
        const counts = { image: 0, audio: 0, video: 0 };
        canvasInputs.value.gallery.forEach(r => counts[r.kind]++);
        if (!Object.values(counts).some(Boolean)) return null;
        return h("section", { class: "comfyui-reference-counts", style: { marginTop: "12px", display: "flex",
          flexWrap: "wrap", gap: "6px 16px", color: "var(--el-text-color-secondary)", fontSize: "12px" } },
          Object.entries(counts).filter(([, count]) => count).map(([kind, count]) =>
            h("span", {}, `画布参考${Core.names[kind]}${count}`)));
      };
      const mediaThumb = r => {
        const src = previewUrls.value[r.key];
        const fallback = h("span", { class: "comfyui-media-kind" }, Core.names[r.kind]);
        if (r.kind === "image" && src) return [fallback, h("img", { src, alt: r.alias, draggable: false,
          onError: e => { e.target.style.visibility = "hidden"; } })];
        if (r.kind === "video" && src) return [fallback, h("video", { src, muted: true, preload: "metadata", playsinline: true,
          onError: e => { e.target.style.visibility = "hidden"; } })];
        return fallback;
      };
      const composer = () => !composerOpen.value ? null : h("section", {
        class: "nodrag nopan nowheel comfyui-composer", onClick: e => e.stopPropagation(), onKeydown: e => e.stopPropagation()
      }, [
        h("div", { class: "comfyui-composer-top" }, [
          h("strong", {}, "提示词"),
          h("div", { style: { display: "flex", flexWrap: "wrap", gap: "4px" } }, [
            canvasInputs.value.texts.length ? smallButton("载入文字", useCanvasPrompt, { text: true, disabled: running.value,
              title: "将已连接文字节点的提示词载入当前输入框" }) : null,
            smallButton("@", () => {
              editorElement?.focus(); rememberCaret();
              mentionQuery.value = ""; mentionIndex.value = 0; mentionRange = undefined;
            }, { text: true, disabled: running.value, title: "引用连接的图片、音频或视频", "aria-label": "插入参考素材" })
          ])
        ]),
        canvasInputs.value.gallery.length ? h("div", { class: "comfyui-connected-media", "aria-label": "已连接参考素材" },
          canvasInputs.value.gallery.map(r => h("button", { key: r.key, type: "button", class: "comfyui-media-tile",
            "aria-label": `引用${r.alias}`, title: `${r.alias} · ${r.label}`, disabled: running.value,
            onMousedown: e => e.preventDefault(), onClick: () => insertReference(r) }, [
              h("div", { class: "comfyui-media-thumb" }, mediaThumb(r)),
              h("span", { class: "comfyui-media-alias" }, r.alias)
            ]))) : null,
        h("div", { class: "comfyui-prompt-wrap" }, [
          h("div", { key: "prompt-editor", ref: setEditorElement, class: "comfyui-prompt-editor nodrag nopan nowheel",
            contenteditable: running.value ? "false" : "true", role: "textbox", "aria-label": "ComfyUI 提示词",
            "aria-multiline": "true", spellcheck: false,
            "data-placeholder": canvasInputs.value.texts.length ? "沿用已连接文字节点的提示词" : "输入提示词",
            onInput: onPromptInput, onKeydown: onPromptKeydown, onKeyup: event => {
              if (!["ArrowDown", "ArrowUp", "Enter", "Escape"].includes(event.key)) updateMention();
            }, onClick: updateMention, onMouseup: rememberCaret, onPaste: onPromptPaste, onCopy: onPromptCopy, onCut: onPromptCopy,
            onCompositionstart: () => { composing = true; mentionQuery.value = null; },
            onCompositionend: () => { composing = false; onPromptInput(); },
            onBlur: () => { mentionQuery.value = null; mentionRange = undefined; },
            onDrop: event => event.preventDefault()
          }),
          mentionQuery.value === null ? null : h("div", { class: "comfyui-mention-menu", role: "listbox", "aria-label": "选择参考素材" },
            mentionItems.value.length ? mentionItems.value.map((r, i) => h("button", {
              key: r.key, type: "button", role: "option", "aria-selected": i === mentionIndex.value,
              class: "comfyui-mention-option", title: r.label, onMousedown: e => e.preventDefault(),
              onClick: () => insertReference(r)
            }, [
              h("span", { class: "comfyui-mention-thumb" }, mediaThumb(r)),
              h("span", {}, r.alias), h("span", { class: "comfyui-mention-label" }, r.label)
            ])) : h("span", { class: "comfyui-mention-empty" }, canvasInputs.value.gallery.length ? "没有匹配素材" : "暂无连接素材"))
        ])
      ]);
      const outputPreview = () => {
        if (!outputUrl.value) return null;
        const filename = outputEntriesRef.value.find(e => outputUrl.value.includes(encodeURIComponent(e.filename)))?.filename || outputEntriesRef.value[0]?.filename || "";
        const video = /\.(mp4|webm|mov)$/i.test(filename), audio = /\.(wav|mp3|flac|ogg|m4a)$/i.test(filename);
        return h(video ? "video" : audio ? "audio" : "img", { src: outputUrl.value, alt: "ComfyUI 输出", controls: video || audio,
          style: { display: "block", width: "100%", maxHeight: "220px", objectFit: "contain", marginTop: "12px", borderRadius: "5px" } });
      };
      return () => h(nodeSkeleton, {
        label: data.label || "ComfyUI 工作流",
        handles: declaredHandles,
        outputs: data.outputs,
        style: { width: `min(${management.value ? 980 : composerOpen.value || parameterEditorOpen.value ? 600 : 460}px, calc(100vw - 32px))` }
      }, { default: () => h("div", {
        class: "comfyui-node",
        onClick: event => {
          if (management.value) return;
          const target = event.target;
          if (target && typeof target.closest === "function" && target.closest("input,textarea,select,button,[contenteditable],.comfyui-composer,.comfyui-parameters")) return;
          toggleComposer();
        },
        style: { width: "100%", minWidth: "0", color: "var(--el-text-color-primary)", fontSize: "13px", letterSpacing: "0" }
      }, [
        h("style", {}, `
          @keyframes comfyui-progress-wait{from{transform:translateX(-110%)}to{transform:translateX(390%)}}
          .comfyui-progress-track.is-indeterminate .comfyui-progress-fill{animation:comfyui-progress-wait 1.3s linear infinite}
          @media(prefers-reduced-motion:reduce){.comfyui-progress-track.is-indeterminate .comfyui-progress-fill{animation:none}}
          .comfyui-scroll::-webkit-scrollbar{width:12px;height:12px}
          .comfyui-scroll::-webkit-scrollbar-track{background:var(--el-bg-color)}
          .comfyui-scroll::-webkit-scrollbar-thumb{background:var(--el-border-color);border:2px solid var(--el-bg-color);border-radius:6px;min-height:32px}
          .comfyui-scroll::-webkit-scrollbar-thumb:hover{background:var(--el-text-color-secondary)}
          .comfyui-composer{margin-top:12px;border:1px solid var(--el-border-color);border-radius:8px;background:var(--el-bg-color)}
          .comfyui-composer:focus-within{border-color:var(--el-color-primary)}
          .comfyui-composer-top{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 10px}
          .comfyui-connected-media{display:flex;gap:8px;padding:2px 12px 10px;overflow:auto;max-height:120px}
          .comfyui-media-tile{flex:0 0 64px;width:64px;border:0;padding:0;background:transparent;color:inherit;cursor:pointer;font:inherit}
          .comfyui-media-thumb{position:relative;width:64px;height:54px;border:1px solid var(--el-border-color-lighter);border-radius:5px;overflow:hidden;background:var(--el-fill-color-light);display:flex;align-items:center;justify-content:center}
          .comfyui-media-thumb img,.comfyui-media-thumb video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
          .comfyui-media-tile:hover .comfyui-media-thumb{border-color:var(--el-color-primary)}
          .comfyui-media-kind{font-size:11px;color:var(--el-text-color-secondary)}
          .comfyui-media-alias{display:block;font-size:11px;line-height:20px;white-space:nowrap}
          .comfyui-prompt-wrap{position:relative;min-width:0}
          .comfyui-prompt-editor{min-height:116px;max-height:280px;overflow:auto;padding:10px 12px 14px;outline:none;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;font-size:13px}
          .comfyui-prompt-editor[data-empty="true"]:before{content:attr(data-placeholder);color:var(--el-text-color-secondary);pointer-events:none}
          .comfyui-prompt-chip{display:inline-flex;vertical-align:middle;align-items:center;gap:4px;max-width:100%;border:1px solid var(--el-border-color-lighter);border-radius:5px;background:var(--el-fill-color-light);padding:0 5px;margin:0 2px;font-size:12px;line-height:26px;white-space:normal}
          .comfyui-prompt-chip img{width:22px;height:22px;object-fit:cover;border-radius:3px}
          .comfyui-prompt-chip.is-disconnected{color:var(--el-color-danger);border-color:var(--el-color-danger)}
          .comfyui-mention-menu{position:absolute;left:8px;right:8px;top:100%;z-index:100;max-height:224px;overflow:auto;background:var(--el-bg-color-overlay);border:1px solid var(--el-border-color);border-radius:6px;padding:4px;box-shadow:0 4px 14px #00000018}
          .comfyui-mention-option{width:100%;display:flex;align-items:center;gap:8px;text-align:left;border:0;border-radius:4px;color:inherit;background:transparent;padding:5px;cursor:pointer;font:inherit}
          .comfyui-mention-option[aria-selected="true"],.comfyui-mention-option:hover{background:var(--el-color-primary-light-9)}
          .comfyui-mention-thumb{position:relative;display:flex;align-items:center;justify-content:center;flex:0 0 30px;width:30px;height:30px;overflow:hidden;border-radius:4px;background:var(--el-fill-color-light)}
          .comfyui-mention-thumb img,.comfyui-mention-thumb video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
          .comfyui-mention-label{flex:1;min-width:0;color:var(--el-text-color-secondary);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
          .comfyui-mention-empty{display:block;padding:8px;color:var(--el-text-color-secondary)}
          @media(max-width:640px){.comfyui-node .comfyui-management{grid-template-columns:minmax(0,1fr)!important}.comfyui-node .comfyui-workflow-list{border-right:0!important;border-bottom:1px solid var(--el-border-color-lighter)}.comfyui-node .comfyui-parameter-values{grid-template-columns:minmax(0,1fr)!important}}
        `),
        h("header", { style: { display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "10px", alignItems: "center",
          padding: "8px", borderBottom: "1px solid var(--el-border-color-light)", background: "var(--el-bg-color-overlay)" } }, [
          management.value ? h("strong", { style: { fontSize: "16px" } }, "ComfyUI 工作流管理") : h("span"),
          management.value ? h("label", { style: { display: "flex", alignItems: "center", gap: "8px", flex: "1 1 260px", maxWidth: "370px", fontSize: "12px" } },
            [h("span", {}, "连接使用设置 → MiniMax H3 / ComfyUI 中保存的地址")]) : null,
          smallButton(management.value ? "返回工作流" : "管理", e => { e.stopPropagation(); management.value = !management.value; }, { text: true, disabled: running.value || detecting.value })
        ]),
        management.value ? h("div", { class: "comfyui-management", style: { display: "grid", gridTemplateColumns: "150px minmax(0,1fr)", minHeight: "400px", border: "1px solid var(--el-border-color-light)", borderTop: "0", borderRadius: "0 0 8px 8px", overflow: "hidden" } }, [
          h("aside", { class: "comfyui-workflow-list", style: { padding: "14px 10px", borderRight: "1px solid var(--el-border-color-lighter)", background: "var(--el-fill-color-lighter)" } }, [
            sectionHeading("已保存工作流", [smallButton("+", addWorkflow, { title: "新增工作流", "aria-label": "新增工作流", disabled: detecting.value })]),
            ...workflows.value.map(item => h("div", { key: item.id, class: "comfyui-workflow-item",
              style: { display: "flex", alignItems: "center", gap: "2px", marginTop: "8px", minWidth: "0" } }, [
              h("button", { disabled: detecting.value, style: { display: "block", flex: "1", minWidth: "0", padding: "9px 8px",
              border: "0", textAlign: "left", borderRadius: "5px", cursor: "pointer", overflowWrap: "anywhere", fontSize: "12px",
              background: item.id === selectedWorkflow.value ? "var(--el-color-primary-light-9)" : "transparent", color: item.id === selectedWorkflow.value ? "var(--el-color-primary)" : "inherit" },
                onClick: () => selectWorkflow(item) }, item.name),
              smallButton("×", e => { e.stopPropagation(); requestLibraryChange(item); }, { text: true, type: "danger",
                title: `删除工作流 ${item.name}`, "aria-label": `删除工作流 ${item.name}`,
                style: { flex: "0 0 24px", width: "24px", minHeight: "28px", padding: "0", margin: "0" },
                disabled: detecting.value || running.value })
            ]))
          ]),
          h("div", { class: "nodrag nopan", onClick: e => e.stopPropagation(), style: { padding: "14px", minWidth: "0", background: "var(--el-bg-color)" } }, [
            field("工作流名称", textInput(workflowName.value, e => { workflowName.value = e.target.value; }, "例如：H3 视频生成")),
            field("API Format JSON", h("textarea", { ...scrollProps, value: workflowText.value, rows: 7,
              style: { ...controlStyle, ...scrollStyle, resize: "vertical", fontFamily: "monospace", height: "160px", fontSize: "11px" }, onInput: e => { workflowText.value = e.target.value; } })),
            h("div", { style: { display: "flex", gap: "6px", flexWrap: "wrap" } }, [
              smallButton("一键检测", () => detectParameters(false), { type: "primary", plain: true, loading: detecting.value }),
              smallButton("测试连接", testConnection, { disabled: detecting.value }),
              smallButton("导入 JSON", () => fileInput.value?.click(), { disabled: detecting.value }),
              smallButton("保存工作流", saveWorkflow, { type: "primary", disabled: detecting.value }),
              smallButton("一键清除", () => requestLibraryChange(), { type: "danger", plain: true, disabled: detecting.value || running.value }),
              ignoredParameters.value.length || ignoredBindings.value.length ? smallButton("恢复已删项", resetDetection, { text: true, disabled: detecting.value }) : null,
              h("input", { ref: fileInput, type: "file", accept: ".json,application/json", style: { display: "none" }, onChange: importWorkflow })
            ]),
            libraryConfirmationPanel(),
            h("div", { role: "status", style: { marginTop: "10px", color: error.value ? "var(--el-color-danger)" : "var(--el-text-color-secondary)", overflowWrap: "anywhere", fontSize: "12px" } }, error.value || status.value),
            parameterDefinitionEditor(), bindingEditor(), outputDefinitionPanel()
          ])
        ]) : h("div", { class: "nodrag nopan", style: { padding: "12px 8px", background: "var(--el-bg-color)" } }, [
          field("工作流", selectInput(selectedWorkflow.value, [["", workflows.value.length ? "选择已保存工作流" : "暂无工作流"], ...workflows.value.map(item => [item.id, item.name])],
            e => { const item = workflows.value.find(entry => entry.id === e.target.value); if (item) selectWorkflow(item); }, { disabled: running.value })),
          h("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", justifyContent: "space-between" } }, [
            referenceCounts(), smallButton(composerOpen.value ? "收起提示词" : "展开提示词", toggleComposer,
              { text: true, "aria-expanded": composerOpen.value })
          ]),
          composer(), parameterEditor(),
          h("div", { style: { display: "flex", gap: "8px", marginTop: "16px" } }, [
            smallButton(running.value ? "正在运行" : "运行", run, { type: "primary", loading: running.value, disabled: running.value || !workflowText.value }),
            smallButton("中断", stop, { disabled: !running.value })
          ]),
          running.value ? h("div", { class: "comfyui-run-progress", style: { marginTop: "12px" } }, [
            h("div", { style: { display: "flex", flexWrap: "wrap", gap: "6px 8px", justifyContent: "space-between",
              fontSize: "12px", marginBottom: "6px", overflowWrap: "anywhere" } }, [
              h("span", { style: { flexShrink: 0 } }, runProgress.value.stage),
              h("span", { style: { minWidth: 0 } }, runProgress.value.percent === null ? runProgress.value.detail : `${runProgress.value.percent}%`)
            ]),
            h("div", { role: "progressbar", "aria-label": "ComfyUI 运行进度", "aria-valuemin": 0, "aria-valuemax": 100,
              "aria-valuenow": runProgress.value.percent === null ? undefined : runProgress.value.percent,
              "aria-valuetext": [runProgress.value.stage, runProgress.value.detail].filter(Boolean).join(" · "),
              class: runProgress.value.percent === null ? "comfyui-progress-track is-indeterminate" : "comfyui-progress-track",
              style: { height: "6px", overflow: "hidden", borderRadius: "3px", background: "var(--el-fill-color-light)" } }, [
              h("div", { class: "comfyui-progress-fill", style: { height: "100%", width: runProgress.value.percent === null ? "35%" : `${runProgress.value.percent}%`,
                background: "var(--el-color-primary)", transition: "width 180ms ease" } })
            ]),
            runProgress.value.percent !== null && runProgress.value.detail ?
              h("div", { style: { fontSize: "11px", marginTop: "5px", overflowWrap: "anywhere",
                color: "var(--el-text-color-secondary)" } }, runProgress.value.detail) : null
          ]) : null,
          h("div", { role: "status", style: { marginTop: "12px", color: error.value ? "var(--el-color-danger)" : "var(--el-text-color-secondary)", overflowWrap: "anywhere" } }, error.value || status.value),
          promptId.value ? h("div", { style: { color: "var(--el-text-color-secondary)", marginTop: "4px", fontSize: "11px", overflowWrap: "anywhere" } }, `Prompt: ${promptId.value}`) : null,
          outputPreview()
        ])
      ]) });
    }
  });
});
