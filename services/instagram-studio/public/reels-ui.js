let file=null,objectUrl='',metadata=null,videoError='',busy=false,asset=null,jobId=null;
let caption='',shareToFeed=true,requestId=crypto.randomUUID(),poller;
try{caption=(localStorage.getItem('teoksang-reel-caption-v1')??'').slice(0,2200);}catch{}
const labels={queued:'게시 대기',creating:'영상 전송 중',processing:'Instagram 처리 중',publishing:'게시 중',published:'게시 완료',failed:'게시 실패',uncertain:'결과 확인 필요'};
export function stopReelPolling(){clearInterval(poller);}
function historyHtml(jobs,esc){return jobs.length?jobs.map(job=>`<div class="reel-job"><div><strong>${esc(job.caption.slice(0,45)||'설명 없는 릴스')}</strong><small>${new Date(job.created).toLocaleString('ko-KR')}</small></div><span class="status ${job.status==='published'?'sent':job.status}">${labels[job.status]??esc(job.status)}</span>${job.reason?`<p>${esc(job.reason)}</p>`:''}</div>`).join(''):'<div class="reel-empty-history">게시한 릴스가 여기에 표시돼요.</div>';}
export function renderReels(ctx){const {esc,icon}=ctx;const ready=ctx.reels.ready&&!ctx.browserMode;
  return `<div class="page-heading"><div><h1>릴스, 여기서 바로.</h1><p>영상과 설명을 준비하고 Instagram에 게시하세요.</p></div><div class="heading-actions"><span class="mode-pill">${ready?'게시 서버 연결됨':'미리보기 모드'}</span></div></div>
  <div class="reels-layout"><div class="reels-editor"><section class="editor-card"><div class="reel-section-title"><span>01</span><h3>영상 선택</h3><span class="tag">9:16 권장</span></div><input id="reel-file" class="visually-hidden" type="file" accept="video/mp4,.mp4" aria-label="릴스 영상 선택"><label for="reel-file" class="drop-zone" id="reel-drop" tabindex="0" role="button"><span class="upload-symbol">${icon('video')}</span><strong>${file?esc(file.name):'영상을 끌어 놓거나 선택하세요'}</strong><span>${file?`${(file.size/1024/1024).toFixed(1)} MB · 다른 영상으로 바꾸기`:'MP4 · 최대 100MB · 3초~15분'}</span></label><div id="reel-file-note" class="reel-file-note">${videoError?esc(videoError):metadata?`${metadata.width} × ${metadata.height} · ${Math.round(metadata.duration)}초`:'선택한 영상은 내 기기에서 먼저 미리 봅니다.'}</div></section>
  <form id="reel-form" class="editor-card reel-caption-card"><div class="reel-section-title"><span>02</span><h3>게시 내용</h3></div><label>설명과 해시태그<textarea id="reel-caption" name="caption" rows="5" maxlength="2200" placeholder="영상에 담은 이야기를 적어주세요.\n\n#릴스 #내브랜드">${esc(caption)}</textarea></label><div class="caption-tools"><span id="reel-char-count">${[...caption].length} / 2,200</span><button type="button" id="save-reel-caption">설명 저장</button></div><label class="check-label"><input id="reel-share" type="checkbox" ${shareToFeed?'checked':''}>프로필 피드에도 표시</label><button class="button primary full" id="reel-publish" type="submit" ${!ready||!file||!metadata||videoError||busy||jobId?'disabled':''}>${icon('send')} ${busy?'게시 요청 중…':jobId?'게시 요청됨':'Instagram에 게시'}</button><p class="reel-publish-note">${ready?'게시 버튼을 누르면 이 영상과 설명이 연결된 Instagram 계정에 공개됩니다.':'미리보기와 설명 저장은 바로 사용할 수 있어요. 실제 게시는 서버·계정 연결 후 가능합니다.'}</p><p id="reel-progress" role="status" class="reel-progress"></p>${!ready?'<a href="#settings" class="reel-connect-link">계정 연결 안내 보기 ↗</a>':''}</form></div>
  <aside class="reels-preview"><div class="device-caption"><span>Instagram 릴스 미리보기</span><span>PREVIEW</span></div><div class="reel-device ${objectUrl?'has-video':''}"><div class="reel-preview-top"><strong>Reels</strong>${icon('camera')}</div>${objectUrl?`<video id="reel-video" src="${esc(objectUrl)}" playsinline controls preload="metadata"></video>`:`<div class="reel-placeholder"><span>${icon('video')}</span><strong>다음 이야기를 들려주세요.</strong><p>영상 하나로 시작하는<br>새로운 연결.</p></div>`}<div class="reel-preview-copy"><span class="reel-brand"><span>dm</span> 내 브랜드</span><p id="reel-caption-preview">${esc(caption||'영상 설명이 여기에 표시돼요.')}</p></div></div><p class="preview-disclaimer">화면은 미리보기이며 실제 Instagram 표시와 다를 수 있어요.</p><div class="reel-history-panel"><h3>최근 게시</h3><div id="reel-history">${historyHtml(ctx.reels.jobs??[],esc)}</div></div></aside></div>`;
}
export function mountReels(ctx){
  stopReelPolling();const $=s=>document.querySelector(s),ready=ctx.reels.ready&&!ctx.browserMode;
  const updateButton=()=>{const button=$('#reel-publish');if(button){button.disabled=!ready||!file||!metadata||!!videoError||busy||!!jobId;button.innerHTML=`${ctx.icon('send')} ${busy?'게시 요청 중…':jobId?'게시 요청됨':'Instagram에 게시'}`;}};
  const video=$('#reel-video'),selectedFile=file;
  if(video){
    function loaded(){
      if(file!==selectedFile||video!==$('#reel-video'))return;
      metadata={duration:video.duration,width:video.videoWidth,height:video.videoHeight};
      videoError=!Number.isFinite(metadata.duration)||metadata.duration<3||metadata.duration>900?'3초 이상, 15분 이하의 영상을 선택해 주세요.':'';
      $('#reel-file-note').textContent=videoError||`${metadata.width} × ${metadata.height} · ${Math.round(metadata.duration)}초`;
      $('#reel-file-note').classList.toggle('error',!!videoError);updateButton();
    }
    video.addEventListener('loadedmetadata',loaded,{once:true});
    video.addEventListener('error',()=>{if(file!==selectedFile||video!==$('#reel-video'))return;videoError='이 브라우저에서 영상을 재생할 수 없습니다. H.264 MP4로 변환한 뒤 다시 선택해 주세요.';$('#reel-file-note').textContent=videoError;updateButton();},{once:true});
    if(video.readyState>=1)loaded();
  }
  async function selectFile(selected){
    if(!selected)return;
    if(busy){ctx.toast('게시 요청이 끝난 뒤 영상을 바꿔주세요.',true);return;}
    if(!/\.mp4$/i.test(selected.name)||selected.size<16||selected.size>100*1024*1024){ctx.toast('100MB 이하의 MP4 영상을 선택해 주세요.',true);return;}
    if(objectUrl)URL.revokeObjectURL(objectUrl);
    file=selected;objectUrl=URL.createObjectURL(file);metadata=null;videoError='';asset=null;jobId=null;requestId=crypto.randomUUID();
    ctx.render();
  }
  $('#reel-file').addEventListener('change',event=>selectFile(event.target.files[0]));
  const drop=$('#reel-drop');drop.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();$('#reel-file').click();}});
  drop.addEventListener('dragover',event=>{event.preventDefault();drop.classList.add('dragging');});
  drop.addEventListener('dragleave',()=>drop.classList.remove('dragging'));
  drop.addEventListener('drop',event=>{event.preventDefault();drop.classList.remove('dragging');selectFile(event.dataTransfer.files[0]);});
  $('#reel-caption').addEventListener('input',event=>{caption=event.target.value;$('#reel-char-count').textContent=`${[...caption].length} / 2,200`;$('#reel-caption-preview').textContent=caption||'영상 설명이 여기에 표시돼요.';});
  $('#reel-share').addEventListener('change',event=>shareToFeed=event.target.checked);
  $('#save-reel-caption').addEventListener('click',()=>{try{localStorage.setItem('teoksang-reel-caption-v1',caption);ctx.toast('설명을 이 브라우저에 저장했어요. 영상 파일은 저장하지 않습니다.');}catch{ctx.toast('브라우저 저장 공간을 확인해 주세요.',true);}});
  $('#reel-form').addEventListener('submit',async event=>{
    event.preventDefault();event.stopPropagation();if(!ready||busy||!file||!metadata||videoError||jobId)return;
    // Snapshot the reviewed content at the user's explicit publish click.
    const selected=file,postCaption=caption,postShare=shareToFeed,postRequest=requestId;busy=true;updateButton();
    const progress=message=>{if($('#reel-progress'))$('#reel-progress').textContent=message;};
    try{
      if(!asset){progress('영상 파일을 게시 서버에 업로드하고 있어요…');
        const response=await fetch(`${ctx.basePath}/api/reels/upload`,{method:'POST',headers:{'Content-Type':'video/mp4','X-File-Name':encodeURIComponent(selected.name)},body:selected});
        const result=await response.json();if(!response.ok)throw new Error(result.error??'영상 업로드에 실패했습니다.');asset=result;
      }
      progress('Instagram 게시 요청을 등록하고 있어요…');
      const result=await ctx.api('/api/reels','POST',{uploadId:asset.id,caption:postCaption,shareToFeed:postShare,requestId:postRequest});jobId=result.id;
      progress('게시 요청을 접수했어요. 영상 처리가 끝나면 게시됩니다. 아래 기록에서 상태를 확인하세요.');ctx.toast('릴스 게시 요청을 접수했어요.');await loadHistory();
    }catch(error){progress(error.message);ctx.toast(error.message,true);}finally{busy=false;updateButton();}
  });
  async function loadHistory(){if(ctx.browserMode)return;try{const result=await ctx.api('/api/reels');const el=$('#reel-history');if(el)el.innerHTML=historyHtml(result.jobs,ctx.esc);const job=result.jobs.find(j=>j.id===jobId);if(job&&$('#reel-progress'))$('#reel-progress').textContent=`${labels[job.status]??job.status}${job.reason?' · '+job.reason:''}`;}catch{/* A later refresh retries read-only status, never the publish request. */}}
  if(!ctx.browserMode)poller=setInterval(()=>{if(!document.hidden)loadHistory();},5000);
}
