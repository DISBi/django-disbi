// After of experiments, at which a warning is displayed.
var tooMuchExps = 20;

function showExperimentInfo() {
	$inputForm = $('#user_input');
	inputFormData = $inputForm.serialize();
	$.ajax({
		url: 'exp_info/',
		type: 'POST',
		data: inputFormData,
		success: function( response ) {
			console.log( response );
			// Update or add a message for the user.
			if ( response.numExps === 1) {
				$( "#num_exps_info" ).text(response.numExps + 
				" experiment meets your requested conditions.");
			} else {
				$( "#num_exps_info" ).text(response.numExps + 
				" experiments meet your requested conditions.");
			}
			if ( response.numExps > 0 ) {
				
				if ( response.numExps >= tooMuchExps ) {
					// Show a warning for too many experiments.
					text = $( "#num_exps_info" ).text();
					$( "#num_exps_info" ).html(text +
							"<span class=\"warning\"> This might take some time.</span>");
				}
				$( "#submit_button" ).show();
				$( "#available-exps" )
					.html(response.tableExps);
				$( "#available-exps" ).show();
			} else {
				$( "#submit_button" ).hide();
				$( "#available-exps" ).hide();
			}
		},
		error: function( xhr, errmsg, err ) {
			console.log( "Error while fetching information about experiments." );
		}
	});
}
	

function gridify( delBtnSize ) {
	// Get the size of the grid.
	console.log( "grid: ", $( ".grid" ).first().width());
	var twelfth = $( ".grid" ).first().width()/ 12;
	// For each subform, compute the number of columns it will need.
	var cols;
	var colsCount = 0;
	var row = $();
	$( ".input-subform" ).each( function() {
		cols = Math.ceil(($( this ).outerWidth() + delBtnSize) / twelfth);
		colsCount += cols;
		if ( colsCount > 12 ) {
			// Wrap all elements of the last row in a grid.
			row.wrapAll( "<div class=\"grid grid-pad\"></div>");
			// Reset the row.
			row = $();
			// Reset the colsCount.
			colsCount = cols;
		}
		row = row.add(this);
		// Add the appropriate layout class.
		$( this ).addClass( `col-${cols}-12` );
	});
	// Wrap the last row that did not reach the end.
	row.wrapAll( "<div class=\"grid grid-pad\"></div>");
	// Remove the grid that was only used to infer the layout.
	$( "#layout-helper" ).contents().unwrap();
}
// Query server in case options are still selected after reload.
showExperimentInfo();

$('select').on('change', function() {
	showExperimentInfo();
});

	
	

