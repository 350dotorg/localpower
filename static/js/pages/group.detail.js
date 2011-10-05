/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["libs/jquery.tablesorter", "mods/invite"], 
    function (tablesorter, invite) {
        $("table").tablesorter();
        invite.setup();

        $("#external_link_buttons a.button").each(function () {
          var link = $(this);
          var container = $("<div class='hidden'></div>");
          $("body").append(container);
          container.load(link.attr("href"), function () {
            $("button, input:submit, a.button, input.button", container).button();
            $("form", container).attr("action", link.attr("href"));
            container.dialog({ 
              autoOpen: false,
              modal: true,
              height: 575,
              width: 360
            });
          });
          link.click(function () {
            container.dialog("open");
            return false;
          });
        });

    });

