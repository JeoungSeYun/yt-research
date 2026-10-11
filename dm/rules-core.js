export function normalize(text) { return String(text).normalize('NFKC').toLocaleLowerCase('ko-KR').trim(); }
export function validateRule(input) {
  if (!input || typeof input !== 'object') throw new Error('규칙을 입력해 주세요.');
  const name = String(input.name ?? '').trim();
  const reply = String(input.reply ?? '').trim();
  const keywords = [...new Set((Array.isArray(input.keywords) ? input.keywords : String(input.keywords ?? '').split(',')).map(normalize).filter(Boolean))];
  if (!name || name.length > 80) throw new Error('규칙 이름은 1~80자로 입력해 주세요.');
  if (!reply || [...reply].length > 1000) throw new Error('답장은 1~1,000자로 입력해 주세요.');
  if (!['dm', 'comment'].includes(input.trigger)) throw new Error('DM 또는 댓글을 선택해 주세요.');
  if (!['contains', 'exact'].includes(input.match)) throw new Error('키워드 매칭 방식을 선택해 주세요.');
  if (!keywords.length || keywords.length > 20 || keywords.some(k => k.length > 100)) throw new Error('키워드는 1~20개, 각각 100자 이하로 입력해 주세요.');
  const cooldown = Number(input.cooldown ?? 60);
  if (!Number.isInteger(cooldown) || cooldown < 0 || cooldown > 10080) throw new Error('재발송 간격은 0~10,080분이어야 합니다.');
  const mediaId = String(input.mediaId ?? '').trim();
  if (mediaId && !/^\d{1,40}$/.test(mediaId)) throw new Error('게시물 ID는 숫자로 입력해 주세요.');
  return { name, reply, keywords, trigger: input.trigger, match: input.match, cooldown, mediaId, enabled: input.enabled === true };
}
export function chooseRule(rules, event) {
  const text = normalize(event.text);
  return rules.find(r => r.enabled && r.trigger === event.trigger && (!r.mediaId || r.mediaId === event.mediaId) &&
    r.keywords.some(k => r.match === 'exact' ? text === k : text.includes(k)));
}
