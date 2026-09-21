/*
 * Toggle the visibility of table cells with the advanced action menu
 */
function toggleAdvancedOptions()
{
	arr = getElementsByTagAndClassName("td", "advancedMenu");
	for (i=0; i<arr.length; i++) {
		if (document.pageOptions.showAdvanced.checked) {
			arr[i].style.display = 'table-cell';
		} else {
			arr[i].style.display = 'none';
		}
	} 
}

function createFilteredView( component, path )
{
	document.location = "/watchers/filtered?" +
			"processes=" + encodeURIComponent( component ) +
			"&path=" + encodeURIComponent( path );
}

// tree.js
