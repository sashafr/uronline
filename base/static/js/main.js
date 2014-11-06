var p3BotbannerHeight = 152;

function getWinHeight() {
  var myHeight = 0;
  if (typeof(window.innerHeight) == 'number') {
    //Non-IE
    myHeight = window.innerHeight;
  } else if (document.documentElement
	     && (document.documentElement.clientWidth 
		 || document.documentElement.clientHeight)) {
    //IE 6+ in 'standards compliant mode'
    myHeight = document.documentElement.clientHeight;
  } else if( document.body && (document.body.clientWidth 
			       || document.body.clientHeight)) {
    //IE 4 compatible
    myHeight = document.body.clientHeight;
  }
  return myHeight;
}

function p3setHeight() {
    var wh = getWinHeight();
    var h = wh - p3BotbannerHeight;
    document.getElementById('content_window').style.height = (h + 'px');
}
