/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["libs/jquery.ui", "libs/markerclusterer"],
    function (ui, markerclusterer) {
        var myOptions = {
            zoom: (RAH.map_center.lat ? 4 : 1),
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            mapTypeControl: false,
            streetViewControl: false,
            zoomControlOptions: {style: google.maps.ZoomControlStyle.SMALL},
            panControl: false, 
            scrollwheel: false,
            center: new google.maps.LatLng(RAH.map_center.lat || 37.000000,
                                           RAH.map_center.lng || -96.000000)
        };
        var gmap = new google.maps.Map(document.getElementById("events_map"), myOptions);
        var geocoder = new google.maps.Geocoder();
        var infowindow = new google.maps.InfoWindow({content: "" });
        var newImage = new google.maps.MarkerImage(RAH.sprite_url, new google.maps.Size(41, 48), new google.maps.Point(232, 104) );

        var style = [{
            url: RAH.sprite_url,
            height: 41,
            width: 48,
            anchor: [14],
            textColor: '#FFFFFF',
            textSize: 12,
            backgroundPosition: "-232px -104px"
        }];
        var markerCluster = new MarkerClusterer(gmap, [], {
            gridSize: 60, 
            styles: style,
            maxZoom: 10
        });

        // store a mapping of latlng -> marker
        // on collisions, we combine the popup html and modify the icon
        var latlngs = {};

        function addUserToMap(geom) {
          var latlng = [geom.lat, geom.lng],
              marker;

          if (latlngs[latlng]) {
            // if the marker already exists,
            // update the icon and append html
            marker = latlngs[latlng];
            marker.info += '<hr />' + geom.info_html;
            marker.setIcon(newImage);
          } else {
            marker = new google.maps.Marker({
              position: new google.maps.LatLng(geom.lat, geom.lng),
              map: gmap,
              info: geom.info_html
            });
            latlngs[latlng] = marker;
            google.maps.event.addListener(marker, 'click', function() {
                infowindow.setContent(this.info);
                infowindow.open(gmap, this);
            });
            markerCluster.addMarker(marker, true);
          }
        }

        // geocode behavior
        $("#map_search .search_widget").submit(function() {
          var address = document.getElementById("search_widget_input").value;
          geocoder.geocode( { 'address': address}, function(results, status) {
            if (status == google.maps.GeocoderStatus.OK) {
              gmap.setCenter(results[0].geometry.location);
                    gmap.fitBounds(results[0].geometry.viewport);
            }
          });
          return false;
        });

        // fetch user data in background
        function fetchBatch(start) {
          jQuery.getJSON(RAH.user_list_url, {start: start}, function(json) {
            if (json.length > 0) {

              jQuery.each(json, function(i, user) {
                // populate list item
                var li = document.createElement('li');
                li.innerHTML = user.list_html;
                RAH.user_list.appendChild(li);

                // add to map
                if (user.geom) {
                  addUserToMap(user.geom);
                }
              });

              // redraw all the clusters at once instead of per user
              markerCluster.redraw();

              fetchBatch(start + RAH.user_list_batch_size);
            } else {
              // we're done loading users at this point
              // free up some memory we're no longer using
              delete latlngs;
            }
          });
        }

        // start async loading of users
        fetchBatch(0);
    });
