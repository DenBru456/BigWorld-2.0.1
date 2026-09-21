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

	<?python
	  import os
	  from web_console.common.util import alterParams

	  pathSplit = watcherData.path.split( "/" )
	?>

	
	<h1 class="watcherheader">Watcher Values for 
		<span py:if="not watcherData.path" py:content="process.label()" py:strip="True"/>
		<span py:if="watcherData.path" py:strip="True">
			<a href="${alterParams( path='' )}">${process.label()}</a>
			<span py:for="i in xrange( len( pathSplit ) - 1 )" py:strip="True">
				/ <a href="${alterParams( path='/'.join( pathSplit[:i+1] ) )}">${pathSplit[i]}</a>
			</span>
			/ ${pathSplit[-1]}
		</span>
	</h1>

	<div py:if="watcherData.isDir()">

		<?python
		  colspan = 4
		?>

		<script type="text/javascript" src="../static/js/collections.js"/>
		<script type="text/javascript" src="../static/js/tree.js"/>

		<form name="menuForm">
		<table class="watcher">
			<tr>
				<td colspan="${colspan}">
				<a py:if="watcherData.path" href="${alterParams( path=os.path.dirname( watcherData.path ) )}">..</a>
				<a py:if="not watcherData.path" href="${tg.url( '/watchers/tree' )}">..</a>
				</td>
			</tr>

			<tr py:for="dir in subDirs" class="watcherrow">
				<td colspan="${colspan}">
					<a href="${alterParams( path=dir.path )}">
						${os.path.basename( dir.path )}
					</a>
				</td>
			</tr>
			<tr py:for="(w, menu) in watchers" class="watcherrow">
				<td>${os.path.basename( w.path )} </td>

				<!-- Check if the watcher is a function or not -->
				<td py:if="w.isCallable()">Callable function</td>
				<td py:if="not w.isCallable()">
					<div py:if="w.isReadOnly()" id="read_only">${w.valueAsStr()}</div>
					<div py:if="not w.isReadOnly()">${w.valueAsStr()}</div>
				</td>

				<!-- The advanced mode options -->
				<td class="advancedMenu" style="display: none">
					<select name="actionMenu" 
						py:replace="actionsMenu( menu, help = 'Add the menu now' )"/>
				</td>
			</tr>
		</table>
		</form>

		<!-- Checkbox to toggle display of custom watcher menu -->
		<form name="pageOptions" py:if="len(watcherData.getChildren()) > 0">
			<input id="advanced" onclick="toggleAdvancedOptions()" type="checkbox" name="showAdvanced"/> <label for="advanced">Advanced Options</label>
		</form>
	</div>

	<div py:if="not watcherData.isDir()">

		<form action="/watchers/tree" method="get">
		<table class="watcher">
			<tr><th class="heading" colspan="2">${watcherData.name}</th></tr>
			<tr>
				<td class="colheader">Existing Value</td>
				<td>${watcherData.value}</td>
			</tr>
			<tr>
				<td class="colheader">New Value</td>
				<td>
					<input type="hidden" name="machine" value="${machine.name}"/>
					<input type="hidden" name="pid" value="${process.pid}"/>
					<input type="hidden" name="path" value="${watcherData.path}"/>
					<input type="hidden" name="dataType" value="${watcherData.type}"/>
					<!-- If it's a boolean, show a dropdown selection -->
					<div py:if="watcherData.type == 4">
						<select name="newval">
							<option value="true">True</option>
							<option value="false">False</option>
						</select>
					</div>
					<div py:if="watcherData.type != 4">
						<input name="newval" value="${watcherData.value}" type="text"/>
					</div>
				</td>
			</tr>
			<tr>
				<td colspan="2" style="text-align:right;">
					<input type="submit" value="Modify"/>
				</td>
			</tr>
		</table>
		
		</form>

	<!-- div py:if="not watcherData.isDir()" -->
	</div>

	<script type="text/javascript">
		if ("${status}" == "False")
		{
			Util.error( "Failed to set value" );
		}
	</script>

<!-- div py:if="pageContent()" -->
</div>

</html>
