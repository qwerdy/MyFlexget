function copyname() {
	var val = document.getElementById('name');

	if(!val) {
		val = document.getElementById('ajax_select');
	}

	if(val) {
		document.getElementById('feed_name').value = val.value;
	}
}