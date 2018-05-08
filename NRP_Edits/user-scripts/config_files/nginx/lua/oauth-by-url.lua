local cjson = require "cjson"

local oauth_url = "/_access_token"
local openid_url = "/_userinfo"
-- how long the cache will stay active, in seconds
local cache_time = 60
local oauth_cache = ngx.shared.oauth_cache

-- probably params from ~/.bbp_services.cfg should be used
local client_id = ngx.var.oidc_client_id
local client_secret = ngx.var.oidc_client_secret

local auth_token = ngx.var.arg_token

if not auth_token then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status": 401, "message": "Missing url token args"}')
    return ngx.exit(ngx.HTTP_OK)
end

--check if we're in the cache
local cached_info = oauth_cache:get(auth_token)
if cached_info ~= nil then
   local user_info = cjson.decode(cached_info)
   ngx.req.set_header("X-User-Name", user_info.sub)
   ngx.req.set_header("X-User-Groups", user_info.groups)
   return
end

local url = oauth_url.."?client_id="..client_id.."&client_secret="..client_secret.."&token="..auth_token
local res = ngx.location.capture(url)
if res.status ~= 200 then
    ngx.status = res.status
    ngx.say(res.body)
    ngx.exit(ngx.HTTP_OK)
end

-- ngx.log(ngx.DEBUG, "OpenId introspect response: "..res.body)
local json = cjson.decode(res.body)
if not json.active then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status":401, "message": "OpenId response: token is not valid"}')
    ngx.exit(ngx.HTTP_OK)
end

url = openid_url.."?access_token="..auth_token
res = ngx.location.capture(url)
if res.status ~= 200 then
    ngx.status = res.status
    ngx.say(res.body)
    ngx.exit(ngx.HTTP_OK)
end

-- ngx.log(ngx.DEBUG, "OpenId userinfo response: "..res.body)
local user_info = cjson.decode(res.body)
if not user_info.sub then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status":401, "message": "Got nil user form userinfo request"}')
    ngx.exit(ngx.HTTP_OK)
end

user_info.type = 'user_auth'
local succ, err, forcible = oauth_cache:set(auth_token, cjson.encode(user_info), cache_time)
if err ~= nil then
   ngx.log(ngx.DEBUG, "Error Adding to cache: "..err)
end
ngx.req.set_header("X-User-Name", user_info.sub)
ngx.req.set_header("X-User-Groups", user_info.groups)
