<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<?python
layout_params['page_specific_css']  = [ "/static/css/help.css" ]
?>

<html xmlns="http://www.w3.org/1999/xhtml"
	xmlns:py="http://purl.org/kid/ns#"
	py:layout="'../../common/templates/layout.kid'"
	py:extends="'../../common/templates/common.kid'"
	xml:lang="en" lang="en">

<div py:def="moduleContent()">

<iframe id="helpFrame"
	width="100%" frameborder="0" src="${HELP_PAGE}"/>


<script type="text/javascript">
	PAGE_TITLE = "${PAGE_TITLE}";
	function resizeHelpFrame()
	{
		var frame = document.getElementById( "helpFrame" );
		var windowSize = getViewportDimensions();
		var framePos = elementPosition( frame );
		frame.height = windowSize.h - framePos.y;
	};

	addLoadEvent( resizeHelpFrame );
	connect( window, "onresize", resizeHelpFrame );
</script>

</div>
</html>

