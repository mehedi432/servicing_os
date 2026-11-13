// SERVICING OS shop / product workflows. No calls outside the logged-in shop.
export async function shopApi(method, args = {}, post = false) {
  const url = new URL('/api/method/servicing_os.api.shop_stock_quick.'+method,window.location.origin)
  const opts = { method: post?'POST':'GET', credentials:'same-origin', headers:{Accept:'application/json'} }
  if(post) {
    const token = window.frappe?.csrf_token || window.csrf_token ||
      decodeURIComponent((document.cookie.split('; ').find(c=>c.startsWith('csrf_token='))||'').split('=').slice(1).join('=')||'')
    opts.headers['Content-Type']='application/json'
    if(token)opts.headers['X-Frappe-CSRF-Token']=token
    opts.body=JSON.stringify(args)
  } else Object.entries(args).forEach(([k,v])=>{if(v!==null && v!==undefined && v!=='')url.searchParams.set(k,String(v))})
  const res=await fetch(url,opts)
  let data
  try{data=await res.json()}catch{throw Error('Unexpected response from SERVICING OS.')}
  if(!res.ok || data.exc || data.exc_type){
    let message=data.exception||'Could not complete request'
    try{let x=JSON.parse(data._server_messages||'[]');if(x.length)message=JSON.parse(x[x.length-1]).message||message}catch{}
    throw Error(String(message).replace(/<[^>]*>/g,''))
  }
  return data.message
}
