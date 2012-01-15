/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
define(["libs/jquery.ui", "mods/facebook", "libs/jquery.validation", "mods/messages"],
    function (ui, facebook, validate, messages) {
        return {
            setup: function (url) {
                var share_mod = this;
                $.get(url, function (data) {
                    share_mod.build_dialog(data);
                });
            },
            build_dialog: function (data) {
                var share_mod = this;
                var container = $("<div>");
                container.html(data);
                container.dialog({ autoOpen: false, modal: true, height: 312, width: 386,
                    title: "Connect with Facebook" });
                $("input.submit, .button, button", container).button();
                $("#ask_to_share").submit(function () {
                    var form = $(this);
                    if ($("#id_has_facebook_access", form).val() !== "True") {
                        FB.login(function (response) {
                            if (response.authResponse) {
                                $.get("/facebook/authorize/", function (data) {
                                    share_mod.share(form);
                                });
                            }
                        }, { scope: "email,publish_stream,offline_access" });
                    } else {
                        share_mod.share(form);
                    }
                    container.dialog("close");
                    return false;
                });
                $("#ask_to_share_cancel", container).click(function () {
                    container.dialog("close");
                    return false;
                });
                $("#id_dont_ask", container).click(function () {
                    $(this).parents("form").submit();
                });
                container.dialog("open");
            },
            share: function (form) {
                var share_mod = this;
                form.ajaxSubmit(function (data) {
                    if ($(".messages", data).length) {
                        messages.add_message(data);
                    } else {
                        share_mod.build_dialog(data);
                    }
                });
            }
        };
    });
