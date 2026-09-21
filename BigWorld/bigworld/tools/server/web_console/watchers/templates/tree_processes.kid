<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<?python
  layout_params[ "pageHeader" ] = "Watchers"
?>

<html xmlns="http://www.w3.org/1999/xhtml"
	  xmlns:py="http://purl.org/kid/ns#"
	  py:layout="'layout.kid'"
	  py:extends="'common.kid'">
	
<div py:def="pageContent()">
	
	<script type="text/javascript">
		PAGE_TITLE = 'Watcher Listing';
	</script>

	<table>
		<th colspan="100" class="heading">Processes for ${user.name}</th>
		<tr class="sortrow">
			<td class="colheader">Process Name</td>
			<td class="colheader">Machine</td>
			<td class="colheader">PID</td>
		</tr>
		<tr py:for="process in processes" class="sortable">
			<!-- Only link to the process watchers if they are supported -->
			<td py:if="process.hasWatchers()"><a href="${tg.url( '/watchers/tree', machine=process.machine.name, pid=process.pid)}">${process.label()}</a></td>
			<td py:if="not process.hasWatchers()">${process.label()}</td>

			<td>${process.machine.name}</td>
			<td>${process.pid}</td>
		</tr>
	</table>

<!-- div py:if="pageContent()" -->
</div>

</html>
