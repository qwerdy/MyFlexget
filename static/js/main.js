function setActive() { //Sets active tabbar
	tab = document.getElementById('list-nav').getElementsByTagName('a');
	for(i=tab.length-1; i; i--) {
		if(document.location.href.indexOf(tab[i].href)>=0) {
			tab[i].id='active';
			return;
		}
	}
	tab[0].id='active';
}

function ajaxRequest(str, replace, cb) {

	if(replace) {
		document.getElementById(replace).innerHTML = "<img src=\"/static/img/ajax-loader.gif\">";
	}

	var http = new XMLHttpRequest();
	http.open("GET", str, true);
	http.onreadystatechange=function() {
		if(http.readyState == 4  && http.status == 200) {
			if(cb) {
				cb(http.responseText);
			} else {
				document.getElementById(replace).innerHTML = http.responseText;
			}
		}
		else {
			if(cb) {
				cb(false);
			} else {
				document.getElementById(replace).innerHTML = "Error getting "+str;
			}
		}
	}
	http.send();
}
