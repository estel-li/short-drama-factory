import {el,field,select} from './api.js';

export function optionsEditor(container,config,presets,skills,current={},onchange=()=>{}){
  container.replaceChildren();
  const values={duration_rule:'total',total_seconds:24,shot_seconds:4,shot_count:6,style:'温暖的二维动漫短剧',genre:'治愈',ratio:'9:16',profile:'draft',seed:12345,auto_reference:true,subtitles:true,h3_mode:'auto',missing_reference:'error',dialogue_language:'Chinese',narration:false,music:'N/A',manual_durations:[],stages:{outline:{provider:'deepseek',model:'',skill:'outline-hook'},storyboard:{provider:'deepseek',model:'',skill:'storyboard-fast'},prompt:{provider:'deepseek',model:'',skill:'h3-t2va'}},...current};
  const controls={};
  function input(name,type='text',list){const item=el('input',{type,value:values[name]});controls[name]=item;if(list){const id='list-'+name+'-'+Math.random().toString(36).slice(2);item.setAttribute('list',id);container.append(el('datalist',{id},list.map(v=>el('option',{value:v}))));}return item}
  function dropdown(name,items){return controls[name]=select(items,values[name])}
  function choice(name,items,type='text'){
    const editor=input(name,type), match=items.some(v=>String(v)===String(values[name]));
    const pick=select([...items.map(value=>({value:String(value),label:String(value)})),{value:'__custom',label:'自定义…'}],match?String(values[name]):'__custom');
    editor.hidden=match;editor.placeholder='填写自定义值';
    pick.addEventListener('change',()=>{editor.hidden=pick.value!=='__custom';if(pick.value!=='__custom')editor.value=pick.value;else editor.focus()});
    return el('div',{},pick,editor);
  }
  const grid=el('div',{class:'grid three'},
    field('视觉风格（可自定义）',choice('style',presets.styles)),field('剧情题材（可自定义）',choice('genre',presets.genres)),
    field('画幅（可自定义）',choice('ratio',presets.ratios)),
    field('时长分配',dropdown('duration_rule',[{value:'total',label:'总时长优先'},{value:'count',label:'镜头数优先'},{value:'manual',label:'手动时长列表'}])),
    field('目标总时长 / 秒',choice('total_seconds',presets.total_seconds,'number')),field('镜头数量',choice('shot_count',presets.shot_counts,'number')),
    field('总时长优先时的每镜头目标 / 秒',choice('shot_seconds',[4,5,6,7,8],'number')),
    field('生成质量',dropdown('profile',Object.entries(config.profiles).map(([value,p])=>({value,label:p.label})))),
    field('手动镜头时长（逗号分隔）',input('manual_durations')));
  controls.manual_durations.value=values.manual_durations.join(',');container.append(grid);
  const stages=el('div',{},el('h3',{},'每阶段文字模型与 Skill'));
  const stageControls={};
  for(const [name,label] of [['outline','大纲'],['storyboard','分镜'],['prompt','H3 提示词']]){
    const value=values.stages[name]||{}, provider=select(config.providers.map(p=>({value:p.id,label:p.name})),value.provider||'deepseek');
    const model=el('input',{value:value.model||'',placeholder:'留空继承提供商默认模型'}), skill=select(skills.filter(s=>s.stage===name).map(s=>({value:s.id,label:s.name})),value.skill);
    stageControls[name]={provider,model,skill};stages.append(el('div',{class:'stage-row grid three'},field(label+' · 提供商',provider),field('模型名',model),field('Skill',skill)));
  }
  container.append(stages);
  const advanced=el('details',{},el('summary',{},'高级与声音设置'),el('div',{class:'grid three'},
    field('随机种子',input('seed','number')),field('H3 模式',dropdown('h3_mode',['auto','T2VA','I2VA','FL2VA','L2VA','Ref2VA'])),
    field('参考缺失策略',dropdown('missing_reference',[{value:'error',label:'报告缺失，等待补齐'},{value:'text',label:'允许降为纯文生'}])),
    field('对白语言',input('dialogue_language')),field('配乐说明',input('music')),field('生成失败额外重试次数（0～2）',input('render_retries','number'))));
  controls.render_retries.value=values.render_retries??1;controls.render_retries.min=0;controls.render_retries.max=2;
  for(const [name,label] of [['auto_reference','自动提取单角色参考'],['subtitles','导出字幕版'],['narration','采用画外旁白'],['allow_long_shots','允许 8～15 秒长镜头（本机默认容量验证范围为 4～8 秒）']]){const item=el('input',{type:'checkbox',checked:values[name]});controls[name]=item;advanced.append(el('label',{class:'check'},item,label));}
  container.append(advanced);
  const reviews={};advanced.append(el('h3',{},'检查模式暂停位置'));for(const [name,label] of [['outline','大纲完成后'],['storyboard','分镜完成后'],['prompt','提示词完成后']]){const check=el('input',{type:'checkbox',checked:(values.review_stages||['outline','storyboard','prompt']).includes(name)});reviews[name]=check;advanced.append(el('label',{class:'check'},check,label))}
  function read(){const result={...values};for(const [name,input] of Object.entries(controls))result[name]=input.type==='checkbox'?input.checked:['total_seconds','shot_seconds','shot_count','seed','render_retries'].includes(name)?Number(input.value):name==='manual_durations'?input.value.split(/[,，]/).filter(v=>v.trim()).map(Number):input.value;result.stages={};for(const [name,row]of Object.entries(stageControls))result.stages[name]={provider:row.provider.value,model:row.model.value.trim(),skill:row.skill.value};result.review_stages=Object.keys(reviews).filter(k=>reviews[k].checked);return result}
  container.onchange=()=>onchange(read());
  return read;
}
