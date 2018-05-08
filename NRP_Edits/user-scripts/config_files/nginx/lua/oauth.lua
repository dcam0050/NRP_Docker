local cjson = require "cjson"

local oauth_url = "/_access_token"
local openid_url = "/_userinfo"

-- how long the cache will stay active, in seconds
local cache_time = 60
local oauth_cache = ngx.shared.oauth_cache


--from the nginx config
local client_id = ngx.var.oidc_client_id
local client_secret = ngx.var.oidc_client_secret
local client_scope = ngx.var.oidc_client_scope
local accept_client_auth = ngx.var.accept_client_auth

--TODO: Remove this once we are using scopes properly
client_scope = client_scope or 'openid'

local client_get_groups = ngx.var.oidc_get_groups
--default is to get groups, to retain old behaviour
client_get_groups = not (client_get_groups ~= nil and string.lower(client_get_groups) == 'false')

local max_sub_request_time = ngx.var.max_sub_request_time
max_sub_request_time = max_sub_request_time or 30

--get the results of GET on `url`
function get_url(url)
    local start_time = ngx.now()
    local result = ngx.location.capture(url)

    if ngx.now() - start_time > max_sub_request_time then
        ngx.log(ngx.DEBUG, 'Sub request to '..url..' took a long time: '..(ngx.now() - start_time))
    end

    return result
end

function set_user_header(user_info)
   ngx.req.set_header("X-User-Name", user_info.sub)
   if client_get_groups then
      ngx.req.set_header("X-User-Groups", user_info.groups)
   end
end

local auth_header = ngx.req.get_headers()["Authorization"]
if not auth_header then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status": 401, "message": "No Authorization header"}')
    return ngx.exit(ngx.HTTP_OK)
end

local pars = string.gmatch(auth_header, "%S+")
local bearer, auth_token, extra = pars(), pars(), pars()
if not auth_token or extra or not bearer or 'bearer' ~= string.lower(bearer) then
    ngx.log(ngx.DEBUG, "Missing Bearer: "..auth_header)
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status": 401, "message": "Incorrect Authorization header"}')
    return ngx.exit(ngx.HTTP_OK)
end

function set_cache(cache_value)
    local succ, err, forcible = oauth_cache:set(auth_token, cache_value, cache_time)
    if err then
       ngx.log(ngx.DEBUG, "Error Adding to cache: "..err)
    end
end

-- check if we're in the cache, Note: a user may have a invalid token
-- during the period that cache_time is set to, and still be considered valid
local cached_info = oauth_cache:get(auth_token)
if cached_info then
   local user_info = cjson.decode(cached_info)
   if user_info.type == 'user_auth' then
      set_user_header(user_info)
   end
   return
end

local url = oauth_url.."?client_id="..client_id.."&client_secret="..client_secret.."&token="..auth_token
local res = get_url(url)
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

-- check if the string `scopes` contains a match to our client_scope
-- returns if allowed, otherwise, signals that this is unauthorized,
-- and doesn't return
function check_scope(client_scope, scopes)
    for scope in scopes:gmatch("%S+") do
        if client_scope == scope then
            return true
        end
    end
    return false
end
if not check_scope(client_scope, json.scope) then
    ngx.log(ngx.DEBUG, "failed check_scope: "..json.scope)
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status": 401, "message": "Not in scope: '..client_scope..'"}')
    return ngx.exit(ngx.HTTP_OK)
end

-- if client authentication is accepted and json.sub matches the clientid
-- and not the user id as for user triggered requests
if accept_client_auth and json.sub == json.client_id then
    client_info = cjson.encode({type = "client_auth"})
    set_cache(client_info)
    return -- we skip getting the user information
end

url = openid_url.."?access_token="..auth_token
if not client_get_groups then
   url = url.."&groups=false"
end
res = get_url(url)
if res.status ~= 200 then
    ngx.log(ngx.DEBUG, "Request to openid_url failed.")
    ngx.status = res.status
    ngx.say(res.body)
    ngx.exit(ngx.HTTP_OK)
end

--ngx.log(ngx.DEBUG, "OpenId userinfo response: "..res.body)
local user_info = cjson.decode(res.body)
if not user_info.sub then
    ngx.log(ngx.DEBUG, "Got nil user form userinfo request")
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say('{"status":401, "message": "Got nil user form userinfo request"}')
    ngx.exit(ngx.HTTP_OK)
end
user_info.type = 'user_auth'
set_cache(cjson.encode(user_info))
set_user_header(user_info)
