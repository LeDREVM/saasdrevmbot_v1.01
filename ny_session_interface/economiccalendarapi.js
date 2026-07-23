const http = require('https');

const options = {
	method: 'GET',
	hostname: 'economic-calendar-api1.p.rapidapi.com',
	port: null,
	path: '/v1/health',
	headers: {
		'x-rapidapi-key': '075945bc84msha034fd1e79929f0p17f56fjsne33786778257',
		'x-rapidapi-host': 'economic-calendar-api1.p.rapidapi.com',
		'Content-Type': 'application/json'
	}
};

const req = http.request(options, function (res) {
	const chunks = [];

	res.on('data', function (chunk) {
		chunks.push(chunk);
	});

	res.on('end', function () {
		const body = Buffer.concat(chunks);
		console.log(body.toString());
	});
});

req.end();