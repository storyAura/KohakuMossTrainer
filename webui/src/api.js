// 后端 API 客户端(/api/v1/*;开发时由 vite 代理到 127.0.0.1:8787)。只做传输,不持有状态。

async function send(method, path, body) {
  const r = await fetch(path, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!r.ok) {
    let detail = ''
    try { detail = (await r.json()).detail || '' } catch { /* 非 JSON 错误体 */ }
    throw new Error(typeof detail === 'string' && detail ? detail : 'HTTP ' + r.status)
  }
  return r.json()
}

export const getJson = path => send('GET', path)
export const postJson = (path, body) => send('POST', path, body || {})
export const putJson = (path, body) => send('PUT', path, body || {})

export const fileUrl = path => '/api/v1/file?path=' + encodeURIComponent(path)

// SSE 订阅;返回带 close() 的句柄。终态后服务端关流。
export function subscribeJobEvents(jobId, onEvent) {
  const es = new EventSource('/api/v1/jobs/' + jobId + '/events')
  es.onmessage = e => {
    try { onEvent(JSON.parse(e.data)) } catch { /* 忽略坏帧 */ }
  }
  es.onerror = () => { es.close() }
  return es
}
