import {api,el,field} from "./api.js?v=3.3.0";
import {dialog} from "./ui.js?v=3.3.0";

const size=value=>`${(value/1024**3).toFixed(2)} GB`;

export function videoWorkflowControls(config, profile, onSaved) {
  const note=el("p",{class:"field-help",role:"status"});
  const progress=el("progress",{max:100,value:0,hidden:true});
  let running=false;
  const run=async work=>{if(running)return;running=true;prepare.disabled=true;try{await work()}catch(error){note.textContent=error.message}finally{running=false;prepare.disabled=false}};
  const observe=async jobId=>{
    progress.hidden=false;
    while(root.isConnected){
      const [state,jobs]=await Promise.all([api("/api/video/workflows/progress"),api("/api/jobs")]);
      const job=jobs.find(j=>j.id===jobId);
      if(state.job_id===jobId){
        const p=state.progress;
        note.textContent=state.message+(p?.total?` · ${size(p.bytes||0)} / ${size(p.total)}`:"");
        if(p?.total)progress.value=Math.min(100,(p.bytes||0)/p.total*100);
        if(["done","paused","error"].includes(state.status))break;
      }
      if(job&&["done","paused","error"].includes(job.status)){note.textContent=job.message;break}
      await new Promise(resolve=>setTimeout(resolve,1200));
    }
    progress.hidden=true;
  };
  const prepare=el("button",{onclick:()=>run(async()=>{
    note.textContent="正在检查所选工作流、已有模型与节点……";
    const plan=await api(`/api/video/workflows/plan?profile=${encodeURIComponent(profile.value)}`);
    if(plan.ready){note.textContent="工作流附加资源已就绪，无需下载；基础 H3 模型可在“模型与环境”检查。";return}
    if(plan.requires_confirmation){
      const choice=await dialog("准备视频工作流",`预计下载 ${size(plan.download_bytes)}。文件：${[...plan.models,...plan.plugins].filter(f=>f.action==="download").map(f=>f.name).join("、")}。本地文件先校验复用，后台下载支持暂停续传。`,[{label:"取消",value:"cancel"},{label:"确认下载并准备",value:"prepare",primary:true}]);
      if(choice!=="prepare")return;
    }
    const result=await api("/api/video/workflows/prepare",{profile:profile.value,download_confirmation:plan.confirmation_token||""});
    note.textContent="准备任务已排队，可以继续编辑；生成前请等待环境就绪。";
    await observe(result.job_id);
  })},"准备所选工作流");
  const stop=el("button",{onclick:async()=>{try{await api("/api/video/workflows/stop",{});note.textContent="已请求暂停，模型下载断点会保留。"}catch(error){note.textContent=error.message}}},"暂停准备");
  const custom=el("button",{onclick:()=>editProfile(config,profile,onSaved,note)},"自定义参数 / 另存方案");
  const root=el("div",{class:"option-section"},el("div",{class:"actions"},prepare,custom,stop),progress,note);
  const explain=()=>{
    const p=config.profiles[profile.value]||{};
    const advanced={
      'h3-audio-drive':'在单镜素材里绑定“驱动原声”，可加首帧控制人物。音轨在采样时锁定，成片使用原声；口型效果仍需试听验看。',
      'h3-foley':'绑定“工作流源视频”，H3 模式选择 T2VA。保留源画面，只生成环境音、动作音或描述的声音。',
      'h3-keyframe-guide':'绑定“中段引导图”，在指定比例的时间点引导构图；可同时使用手动首帧和尾帧。',
      'h3-motion-context':'绑定“工作流源视频”，使用 T2VA 或 Ref2VA，移除独立首尾帧。取末尾多帧与声音接续，去掉重复头部，交付帧数保持目标时长。',
      'h3-canny-control':'绑定“工作流源视频”，逐帧提取轮廓来约束动作与构图。源视频按项目尺寸处理，阈值与控制强度可调。',
    };
    note.textContent=advanced[p.workflow]|| (p.workflow==="lightx2v-8"?"使用独立 8 步 LoRA，适合文字、首帧与首尾帧；多图参考请选择 PDD 或原生方案。":
      p.workflow==="pdd-upscale"?`先生成后用神经网络放大 ${p.upscale_by||1.25} 倍，${p.refine_denoise===0?"不重绘":"以最后一个训练块轻精修"}，保留第一遍音频。`:
      p.workflow==="pdd-8"?"PDD 使用专门的头权重与训练 sigma 网格，不叠加 Turbo LoRA；支持 4、6、8 步。":"原生 H3 工作流；已有模型继续复用。可另存不同的分辨率和采样设置。");
  };
  profile.addEventListener("change",explain);explain();
  return root;
}

function editProfile(config,profile,onSaved,note) {
  const base=config.profiles[profile.value];
  const modal=el("dialog",{class:"modal"});
  const label=el("input",{value:base.label+" · 自定义",maxLength:200});
  const controls={};
  const specs=[['megapixels','生成分辨率（百万像素）',0.1,4,0.1],['steps','采样步数',1,100,1]];
  if(!base.workflow?.startsWith('h3-'))specs.push(['lora_strength','LoRA 强度',-2,2,0.05]);
  if(base.workflow?.startsWith("pdd"))specs.push(['head_strength','PDD 头强度',0,2,0.05]);
  if(base.workflow==="pdd-upscale")specs.push(['upscale_by','潜空间放大倍数',1,2,0.25],['refine_denoise','精修强度（0 关闭 / 0.125 单块）',0,0.125,0.125]);
  if(['h3-audio-drive','h3-foley','h3-canny-control'].includes(base.workflow))specs.push(['source_start_seconds','源素材起点（秒）',0,15,0.1]);
  if(base.workflow==='h3-keyframe-guide')specs.push(['guide_position','引导图在片段中的位置（0～1）',0.01,0.99,0.01]);
  if(base.workflow==='h3-motion-context')specs.push(['context_frames','接续画面帧数（5 / 22 / 39 / 56）',5,56,17],['audio_context_frames','接续声音帧数（0 跟随画面）',0,240,1]);
  if(base.workflow==='h3-canny-control')specs.push(['control_strength','轮廓控制强度',0.05,2,0.05],['control_start','控制起点（采样比例）',0,1,0.01],['control_end','控制终点（采样比例）',0,1,0.01],['canny_low','Canny 低阈值',0.01,0.99,0.01],['canny_high','Canny 高阈值',0.01,0.99,0.01]);
  const defaults={lora_strength:1,head_strength:1,upscale_by:1.25,refine_denoise:0.125,source_start_seconds:0,guide_position:0.5,context_frames:22,audio_context_frames:18,control_strength:0.7,control_start:0,control_end:0.9,canny_low:0.2,canny_high:0.5};
  const inputs=specs.map(([key,title,min,max,step])=>{
    const value=base[key]??defaults[key];
    const control=controls[key]=el("input",{type:"number",value,min,max,step,required:true});
    return field(title,control);
  });
  const error=el("p",{class:"field-help",role:"alert"});
  const close=()=>{modal.close();modal.remove()};
  const save=el("button",{class:"primary",onclick:async()=>{
    save.disabled=true;
    try{
      const changes=Object.fromEntries(Object.entries(controls).map(([key,c])=>{
        if(!c.reportValidity()||c.value.trim()===""||!Number.isFinite(Number(c.value)))throw Error("请填写范围内的有效数值。");
        return [key,Number(c.value)];
      }));
      const result=await api("/api/video/workflows/profiles",{base_profile:profile.value,label:label.value.trim(),changes});
      config.profiles[result.id]=result.profile;
      profile.append(el("option",{value:result.id},result.profile.label));profile.value=result.id;
      profile.dispatchEvent(new Event("change",{bubbles:true}));onSaved();
      note.textContent="自定义方案已保存。请保存当前项目设置后生成。";close();
    }catch(e){error.textContent=e.message}finally{save.disabled=false}
  }},"另存为视频方案");
  modal.append(el("h2",{},"自定义视频工作流参数"),field("方案名称",label),el("div",{class:"grid"},inputs),
    el("p",{class:"field-help"},base.workflow?.startsWith('h3-')?'高级媒体方案使用原生完整采样，默认 12 步；新素材先用短镜头验证。接续上下文不占交付帧数，源音频不足时补静音尾部。':"PDD 基础方案支持 4、6、8 步；LightX2V 和神经放大首遍保持 8 步。调整放大倍数前先少量试镜。"),error,
    el("div",{class:"actions"},el("button",{onclick:close},"取消"),save));
  modal.addEventListener("cancel",()=>modal.remove());document.body.append(modal);modal.showModal();label.focus();
}
