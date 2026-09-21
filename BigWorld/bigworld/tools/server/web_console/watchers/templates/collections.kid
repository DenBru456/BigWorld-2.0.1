<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<?python
  layout_params[ "pageHeader" ] = "Watcher Collections"
?>

<html xmlns="http://www.w3.org/1999/xhtml"
	  xmlns:py="http://purl.org/kid/ns#"
	  py:layout="'layout.kid'"
	  py:extends="'common.kid'">
	
<body>

	<!-- Document body -->
	<div py:def="pageContent()">

	<script type="text/javascript">
		PAGE_TITLE = 'Watcher Collections';
	</script>

	<table py:if="collections">
		<tr class="heading">
			<th>Collection Name</th>
			<th>Actions</th>
		</tr>
		<tr py:for="(collection, menu, count) in collections">
			<td>
			<div py:if="count!=0">
			<a href="${tg.url( 'view', name=collection.pageName )}">
				${collection.pageName}
			</a>
			</div>
			<div py:if="count==0"> ${collection.pageName} </div>
			</td>
			<td align="center">
					<select py:replace="actionsMenu(menu)"/>
			</td>
		</tr>
	</table>

	<div py:if="not collections">
		No watcher collections defined!
	</div>

	<script type="text/javascript" src="../static/js/collections.js"/>
	<p>
		<a href="#" onclick="createCollection( '${user.name}' )">
			New watcher collection
		</a>
	</p>

	</div>
</body>
</html>
