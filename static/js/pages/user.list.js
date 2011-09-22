/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["libs/jquery.ui", "libs/markerclusterer"],
    function (ui, markerclusterer) {
        var myOptions = {
            zoom: 4,
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            mapTypeControl: false,
            streetViewControl: false,
            zoomControlOptions: {style: google.maps.ZoomControlStyle.SMALL},
            panControl: false, 
            scrollwheel: false,
            center: new google.maps.LatLng(RAH.map_center.lat || 37.000000, RAH.map_center.lng || -96.000000)
        };
        var gmap = new google.maps.Map(document.getElementById("events_map"), myOptions);
        var infowindow = new google.maps.InfoWindow({ content: "" });
        var markers = [];
	var latlngs = {};
	var newImage = new google.maps.MarkerImage(RAH.sprite_url, new google.maps.Size(41, 48), new google.maps.Point(232, 104) );
        for (var i = RAH.event_locations.length - 1; i >= 0; i = i - 1) {
            var latlng = [RAH.event_locations[i].lat, RAH.event_locations[i].lon];
            if( latlngs[latlng] ) {
		var marker = latlngs[latlng];
                marker.info += "<hr/>" + RAH.event_locations[i].info;
		marker.setIcon(newImage);
            } else {
              var marker = new google.maps.Marker({
                  position: new google.maps.LatLng(RAH.event_locations[i].lat,
						   RAH.event_locations[i].lon),
                  map: gmap,
                  info: RAH.event_locations[i].info
              });
            }
            latlngs[latlng] = marker;
            markers.push(marker);
        }
	for( var i = RAH.event_locations.length - 1; i >= 0; i = i - 1 ) {
            var marker = markers[i];
            google.maps.event.addListener(marker, 'click', function () {
                infowindow.setContent(this.info);
                infowindow.open(gmap, this);
            });
        }
	delete latlngs;
        var style = [{
            url: RAH.sprite_url,
            height: 41,
            width: 48,
            anchor: [14],
            textColor: '#FFFFFF',
            textSize: 12,
            backgroundPosition: "-232px -104px"
        }];
        var markerCluster = new MarkerClusterer(gmap, markers, {
            gridSize: 60, 
            styles: style,
            maxZoom: 10
        });

    });
