(function() {

	window.debug = {};

	window.debug.log = function(msg) {
		console.log(msg);
	};

	window.debug.error = function(err) {
		console.error(err);
	};

})();