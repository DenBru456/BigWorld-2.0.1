<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<?python
layout_params['page_specific_css'] = [ "/static/css/dynamic_selectors.css" ]
layout_params['page_specific_js']  = [ "/watchers/static/js/filtered.js" ]
?>
<html xmlns="http://www.w3.org/1999/xhtml"
	xmlns:py="http://purl.org/kid/ns#"
	py:layout="'../../common/templates/layout.kid'"
	py:extends="'../../common/templates/common.kid'">

<div py:def="moduleContent()">
	<script type="text/javascript">
		PAGE_TITLE = 'Filtered Tables';
	</script>

	<table class="selection_library">

		<tr py:replace="tableHeader( 'Watcher Filters' )"/>

		<tr>
			<td>
				<div>
					<select size="12" id="saved_filter_list" class="primary_select"/>
				</div>
			</td>
			<td width="100%" valign="top">
				<table class="blank" width="100%">
					<tr>
						<td class="blank" align="right" valign="top">
							<strong>Description:</strong>
						</td>
						<td class="blank" id="description_text">
						</td>
					</tr>
					<tr>
						<td class="blank" align="right">
							<strong>Processes:</strong>
						</td>
						<td class="blank">
							<input type="text" id="process_filter" style="width:100%" value="${processes}"/>
						</td>
					</tr>

					<tr width="100%">
						<td class="blank" align="right">
							<strong>Path:</strong>
						</td>
						<td class="blank" width="100%">
							<input type="text" id="path" style="width:100%" value="${path}"/>
						</td>
					</tr>

					<tr>
						<td class="blank"/>
						<td class="blank" align="left">
							<input type="button" id="fetch" value="Refresh"/>
							<input type="button" id="as_csv" value="Export..."/>
						</td>
					</tr>
					<tr>
						<td class="blank"/>
						<td class="blank" align="left">
							<input type="button" id="save_as" value="Save Filter..."/>
							<input type="button" id="delete" value="Delete"/>
						</td>
					</tr>
				</table>
			</td>
		</tr>
	</table>
	<br/>

	<div id="output_pane"/>
</div>

</html>
