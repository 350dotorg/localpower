$(document).ready(function() {
    rah.base.init();

    // Page templates that require additional js should add an object within the rah object. 
    // then define rahClass to be the name of the object within rah.
    if(undefined !== window.rah_name){
        try{
            rah[rah_name].init();
        }catch(err){}
    }
});

// Object containing all javascript necessary for Repower at Home
var rah = {    
    /**
    * Base contains code that needs to be excecuted with every 
    * page request. e.g., navigation with drop down menus
    **/
    base: {
        init: function(){
            // Setup Feedback dialog
            $("#feedback_dialog").dialog({
                modal:true,
                buttons: {
                    "Submit Feedback": function() { 
                        $("#feedback_form").ajaxSubmit({
                            success: function(messages_html) {
                                $("#feedback_dialog").dialog("close");
                                rah.mod_messages.init(messages_html);
                            },
                        });
                    },
                },
                title: "Feedback",
                autoOpen: false,
                width: 400,
            });
            // Attach functionality to feedback links
            $(".feedback_link").click(function(){
                $("#feedback_dialog").load("/feedback/", function(){ // Load the feedback form via ajax
                    $("#loading").hide();
                    $("#feedback_submit").hide(); // We don't need this button when viewed inside dialog
                    $("#id_url").val(location.href); // Set the url to the current url
                    $("#feedback_dialog").dialog("open"); // Open the dialog with feedback form
                });
                return false;
            });
            rah.mod_messages.init();
            rah.mod_ajax_setup.init();
        },
    },
    
    /**
    * Registration page
    **/
    page_register: {
        init: function(){
            // Funnel step 1: Start on registration page
            _gaq.push(['_trackPageview', '/reg/start']);
            
            // Validate the registration form
            $("#registration_form").validate({
                rules: {
                    email: {
                        required: true,
                        email: true,
                        remote: {
                            url: "/validate/",
                            type: "post",
                        }
                    },
                    first_name: {
        				required: true,
        				minlength: 2
        			},
                    password1: {
        				required: true,
        				minlength: 5
        			},
        			password2: {
        				required: true,
        				minlength: 5,
        				equalTo: "#id_password1"
        			},
                },
                messages: {
                    email: {
                        remote: "That email is already registered",
                    },
                },
                submitHandler: function(form) {                    
                    $(form).ajaxSubmit({
                        dataType: "json",
                        success: function(response, status){
                            if(response['valid'] != true){
                                alert(response['errors']);
                                return;
                            } else {
                                // Set the action of the profile form with the freshly minted user id
                                $("#profile_form").attr("action", "/user/edit/" + response['userid'] + "/");
                                
                                // Show the dialog with profile form
                                $('#dialog').dialog('open');
                                
                                // Funnel step 2: Post registration questions popped up
                                _gaq.push(['_trackPageview', '/reg/questions']);
                            }
                        }
                    });
                }
            });
            // Validate the post registration questions form
            $("#profile_form").validate({
                rules: {
                    zipcode: {
                        remote: {
                            url: "/validate/",
                            type: "post",
                        }
                    },
                },
                messages: {
                    zipcode: {
                        remote: "Please enter a valid 5 digit zipcode",
                    },
                },
            });
        },
    },
    
    /**
    * Profile page
    **/
    page_profile: {
        init: function(){
            rah.mod_action_nugget.init();
            
            // Setup the chart
            if (!chart_data['point_data'].length) {
                $("#chart").html('<img src="' + media_url + 'images/theme/chart_demo.png" alt="sample chart"/>');
            } else {
                var plot = $.plot($("#chart"),
                    [ { data: chart_data['point_data'] }], {
                        series: {
                            lines: { show: true },
                            points: { show: true, radius: 10 },
                            shadowSize: 5,
                        },
                        grid: { hoverable: true, clickable: true, backgroundColor: { colors: ["#DDD", "#FFF"] } },
                        legend: {show: false},
                        xaxis: {mode: "time", autoscaleMargin: 0.1, minTickSize: [1, "day"]},
                        yaxis: {min: 0, tickDecimals: 0},
                });
                $("#chart").bind("plothover", function (event, pos, item) {
                    if (item) {
                        showTooltip(item.pageX, item.pageY, item.dataIndex);
                    }
                    else {
                        $(".chart_tooltip").remove();
                    }
                });
                function showTooltip(x, y, index) {
                    $('<div class="chart_tooltip">' + chart_data["tooltips"][index] + '</div>').css( {
                        position: 'absolute',
                        display: 'none',
                        top: y - 18,
                        left: x + 5 ,
                    }).appendTo("body").fadeIn(300);
                }
            }
            
            // Setup house party form, link, and dialog
            $("#house_party_form").validate({rules: {phone_number: { required: true }}});
            $('#house_party_link').click(function(){ $('#house_party_dialog').dialog('open'); return false; });
            $('#house_party_dialog').dialog({
                title: 'House Party', modal: true, resizable: false, draggable: false, autoOpen: false, 
                buttons: { "Give me a call": function() { $('#house_party_form').submit(); }},
            });
            
            // Setup invite friend form, link, and dialog
            $("#invite_friend_form").validate({rules: {to_email: { required: true, email: true }}});
            $('#invite_friend_link').click(function(){ $('#invite_friend_dialog').dialog('open'); return false; });
            $('#invite_friend_dialog').dialog({
                title: 'Invite a friend', modal: true, autoOpen: false, 
                buttons: { "Send Invitation": function() { $('#invite_friend_form').submit(); }},
            });
            
            // Setup twitter update form, link, and dialog
            $("#twitter_post_dialog").validate({ rules: {status: { required: true, }}});
            $('.twitter_status').click(function(){ $('#twitter_post_dialog').dialog('open'); return false; });
            var form = $('#twitter_status_form');
            $('#twitter_post_dialog').dialog({
                title: 'Tell your tweeps about us', modal: true, autoOpen: false,
                buttons: (form.size() > 0 ? { "Update status": function() { form.submit(); } } : { }),
            });
        },
    },
    
    /**
    * Action Detail page
    **/
    page_action_detail: {
        init: function(){
            var checkboxes = $(".action_task_submitter :checkbox");
            checkboxes.parents('form').find(':submit').remove();
            rah.set_task_completion_submission.init(checkboxes);
            rah.mod_comment_form.init();
        },
    },
    
    /**
    * Action Show page
    **/
    page_action_show: {
        init: function(){
            rah.mod_action_nugget.init();
        },
    },
    
    /**
    * Post (Blog) Detail page
    **/
    page_post_detail: {
        init: function(){
            rah.mod_comment_form.init();
        },
    },
    
    /**
    * Action Nugget
    */
    mod_action_nugget: {
        init: function(){
            this.set_tasks_list_toggle();
            rah.set_task_completion_submission.init($('.action_task_submitter :checkbox'));
        },
        
        set_tasks_list_toggle: function(){
            $('.action_nugget .tasks_link').click(function(){
                $(this).parents('.action_nugget').find('.task_list').slideToggle();
                return false;
            });
        },
    },
   
    set_task_completion_submission: {
        init: function(checkboxes){
            checkboxes.click(function(){
                var form = $(this).parents('form');
                $.post(form.attr('action'), form.serialize(), function(data){
                    rah.mod_messages.init(data['message_html']);
                    try{
                        form.parents('.action_nugget').find('.user_completes').text(data['completed_tasks']);
                    } catch(err){}
                    var box = form.find(':checkbox');
                    box.attr('checked', !box.attr('checked'));
                }, 'json');
                return false;
            });
        }
    },
    
    mod_comment_form: {
        init: function() {
            $("#comment_form").validate({
                rules: {
                    name: { required: true, },
                },
            });
        },
    },
    
    /**
    * mod_messages: call this method to attach message html, if no html is passed it will just set a timer on any existing messages
    **/
    mod_messages: {
      init: function(html) {
          if(html) { $('#message_box').append(html); }
          $(".messages:not(.sticky)").each(function() {
              var elem = $(this).parents("ul");
              setTimeout(function() {
                  elem.slideUp(400, function(){ elem.remove(); });
              }, 3000);
          });
          
          $("#message_box .dismiss").live("click", function(){ $(this).parents("ul").remove(); });
      },
    },
    
    page_password_change: {
        init: function(){            
            // Validate the password form
            $("#password_change_form").validate({
                rules: {
                    old_password: {
                        required: true,
                    },
                    new_password1: {
        				required: true,
        				minlength: 5
        			},
        			new_password2: {
        				required: true,
        				minlength: 5,
        				equalTo: "#id_new_password1"
        			},
                },
            });
        },
    },
    
    page_password_reset_confirm: {
        init: function(){            
            // Validate the password form
            $("#password_reset_confirm").validate({
                rules: {
                    new_password1: {
        				required: true,
        				minlength: 5
        			},
        			new_password2: {
        				required: true,
        				minlength: 5,
        				equalTo: "#id_new_password1"
        			},
                },
            });
        },
    },
    
    mod_ajax_setup: {
        init: function() {
            $.ajaxSetup({
                beforeSend: function() { $("#loading").show(); },
                complete: function() { $("#loading").hide(); },
                error: function(XMLHttpRequest, textStatus) { 
                    var error_html = "<ul class='messages'><li class='messages error'>" + textStatus + "<a href='#' class='dismiss'>close</a></li></ul>"
                    rah.mod_messages.init(error_html);
                },
            });
        },
    },
}