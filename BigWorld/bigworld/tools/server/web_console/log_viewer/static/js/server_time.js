/* namespace */ var ServerTime =
{
	offset: null,
	timezoneOffset: null,

	setOffset: function( serverOffset, timezoneOffset )
	{
		ServerTime.offset = serverOffset;
		ServerTime.timezoneOffset = timezoneOffset;
	},

	asBrowserTime: function()
	{
		return (Date.now() / 1000.0) - ServerTime.timezoneOffset;
	},

	// Convert a server time (expressed in seconds) to a JavaScript Date object
	toDate: function( t )
	{
		return new Date( t * 1000 );
	}
};
