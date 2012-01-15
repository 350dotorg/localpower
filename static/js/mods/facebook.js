/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
define(["https://connect.facebook.net/en_US/all.js"], function (facebook) {
    FB.init({appId: RAH.ENV.facebook_appid, status: true, cookie: true, xfbml: true});
    return {
        setup: function () {
            $("div.fb_button a.fb_button").click(function () {
                FB.login(function (response) {
                    if (response.session) {
                        var next_elem = $("input[type='hidden'][name='next']");
                        var next = next_elem ? next_elem.val() : window.location;
                        window.location = "/facebook/login/?next=" + next;
                    }
                }, { scope: "email"});
            });
        },
        authorize: function () {
            FB.login(function (response) {
                if (response.session) {
                    var next_elem = $("input[type='hidden'][name='next']");
                    var next = next_elem.length ? next_elem.val() : window.location;
                    window.location = "/facebook/authorize/?next=" + next;
                }
            }, { scope: "email"});
            return false;
        }
    };
});
