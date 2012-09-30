function setActive() { //Sets active tabbar
	tab = document.getElementById('list-nav').getElementsByTagName('a');
	for(i=0;i<tab.length;i++) {
		if(document.location.href.indexOf(tab[i].href)>=0) {
			tab[i].id='active';
			return;
		}
	}
	tab[0].id='active';
}

function copyname() {
	document.getElementById('feed_name').value = document.getElementById('name').value;
}
			
function ajaxRequest(str, replace) {

	document.getElementById(replace).innerHTML = "<img src=\"static/img/ajax-loader.gif\">";
	var http = false;
	if(navigator.appName == "Microsoft Internet Explorer") {
		http = new ActiveXObject("Microsoft.XMLHTTP");
	} else {
		http = new XMLHttpRequest();
	}
	http.open("GET", 'ajax?q='+str, true);
	http.onreadystatechange=function() {
		if(http.readyState == 4  && http.status == 200) {
			document.getElementById(replace).innerHTML = http.responseText;
		}
		else {
			document.getElementById(replace).innerHTML = "Error getting "+str;
		}
	}
	http.send();
}
