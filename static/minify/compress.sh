# Min style.css
echo -ne "style.css -> style_min.css ... "
java -jar yuicompressor-2.4.2.jar --type css -o ../css/style_min.css --charset utf-8 ../css/style.css
echo "done"

# Min js_libs.js
echo -ne "js_libs.js -> js_libs_min.js ... "
java -jar yuicompressor-2.4.2.jar --type js -o ../js/js_libs_min.js --charset utf-8 ../js/js_libs.js
echo "done"

# Min rah.js
echo -ne "rah.js -> rah_min.js ... "
java -jar yuicompressor-2.4.2.jar --type js -o ../js/rah_min.js --charset utf-8 ../js/rah.js
echo "done"