var pattern = /s0*(\d+)?[e]0*(\d+)/;
var regPatt = new RegExp(pattern);


function findEpisodeNumber(input) {
	var url = input.value,
	    season = document.querySelectorAll('input[name="season"]')[0],
	    episode = document.querySelectorAll('input[name="episode"]')[0],
	    name = document.querySelectorAll('input[name="name"]')[0],
	    match;

	match = url.toLowerCase().match(regPatt);
	console.log(url);
	console.log(match);

	if(match && match.length === 3) {
		season.value = parseInt(match[1], 10);
		episode.value = parseInt(match[2], 10);
	}

	var dn = url.indexOf('dn=');
	if(dn != -1) {
		dn += 3;
		var end = url.indexOf('&', dn),
		    urlName;
		if(match && match.index) {
			urlName = url.substr(dn, match.index-dn-1)
		} else if(end != -1) {
			urlName = url.substr(dn, end-dn);
		} else {
			urlName = url.substr(dn);
		}

		urlName = urlName.replace(/\+/g, ' ');
		urlName = urlName.replace(/\b./g, function(m){ return m.toUpperCase(); });
		name.value = urlName;
	}

	var name = document.querySelectorAll('input[name="name"]')[0];
	var autocomplete = document.querySelectorAll('select[name="autocomplete"]')[0];

	var shows = ajaxRequest('/shows/ajax/shows',false, function(response) {
		if(response) {
			var shows = JSON.parse(response).shows;

			var opt = document.createElement('option');
			opt.value = '';
			opt.innerHTML = '';
			autocomplete.appendChild(opt);
			for (var i = 0; i < shows.length; i++) {
				opt = document.createElement('option');
				opt.value = shows[i];
				opt.innerHTML = shows[i];
				autocomplete.appendChild(opt);
			};

			name.onkeypress=function(){
				var search = this.value;
				for(var i=0,sL=autocomplete.length;i<sL;i++){
					if(autocomplete.options[i].value.toLowerCase().indexOf(search) === 0){
						autocomplete.selectedIndex = i;
						console.log(autocomplete.options[i]);
						break;
					}
				}
			};

			document.getElementById('label_autocomplete').onclick=function(){
				name.value = autocomplete.options[autocomplete.selectedIndex].value;
			};
		}
	})


}

function copyname() {

}
