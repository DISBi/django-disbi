function embedSVG( params ) {
	$.ajax({
		url: params.url,
		method: "POST",
		data: params.data,
		beforeSend: function() {
			// Remove any warnings.
			$( params.containerId + "--warning" ).empty();
			// Show loading message.
			var $loadingContainer = $( params.containerId + "--loading" );
			$loadingContainer.removeClass( "invisible" );
			$loadingContainer.show();
		},
		success: function( response ) {
			if ( response.status ) {
				console.log( "svg response");
				// Response was ok, attach the plot.
				$( "#plot-container" ).append( '<div class="plot col-1-2">' + response.data + '</div>');
				// Set height and width of the SVG to the values of its bounding box
				// to make it fit the div..
				var lastSVG = $( "svg" ).last()[0];
				var viewBox = lastSVG.getAttribute( "viewBox" ).split(/\s+|,/);
				var plotContainerWidth = viewBox[2];
				var plotContainerHeight = viewBox[3];
				$( "svg" )
					.attr( "height", plotContainerHeight )
					.attr( "width", plotContainerWidth );
				// Attach a delete option to each plot container.
				$( "#plot-container div" ).on( "click", function() {
					$( this ).remove();
				});
				// Scroll to the bottom of the page.
				$( "html, body" ).animate( {scrollTop: $(document).height()}, 1000 );
			} else {
				// Though the request succeeded, no plot could be generated.
				// Show the error message.
				$( params.containerId + "--warning" ).text( response.err_msg );
			}
			
		},
		error: function( xhr, errmsg, err ) {
			// The request did not succeed.
			// Show the HTTP response text as error message.
			console.log( "error while embedding svg" );
			$( params.containerId + "--warning" ).text( xhr.responseText );
		},
		complete: function() {
			// Hide the loading message.
			$( params.containerId + "--loading" ).hide();
		},
	});
}

function makeFooter($table, tableHeaders) {
	$table.append('<tfoot>' + tableHeaders + '</tfoot>');
    
    var idxPattern = /_\d+/;
	//Setup - add a text input to each footer cell.
	$table.find( "tfoot td" ).each( function () {
		var title = $table.find(" thead td" ).eq( $(this).index() ).text();
		var searchbox = '<input type="text" placeholder="Search '+title+'" />';
		var plotBtn = "";
		if (title.match(idxPattern)) {
			plotBtn = '<button type="button" class="action-button">plot '+ title +'</button>';
		}
		
		// Get the name of the column in the footer search box.
		$( this ).html( searchbox + plotBtn );
		// Set listener to plot column distribution on click.
		if (plotBtn !== "") {
			$( this ).find( "button" ).on( "click", function() {
				embedSVG({data: {
					column: title,
					csrfmiddlewaretoken: CSRF_TOKEN,
				},
				url: "get_distribution_plot/",
				containerId: "#plot-distribution"});
			}); 
		}
	});
}

function initTable($table, tableData) {
	var table = $table.DataTable({
    	
	data: tableData,
	dom: 'B<"top"i>rt<"bottom"flp><"clear">',
	scrollY: false,
	scrollX: 'width', // allow scrolling horizontally
	scrollCollapse: true,
	paging: true, // navigation by pages
	ordering: true, // allow ordering columns 
	// show first, previous, number, next and last paging button
	pagingType: "full_numbers",
	deferRender: true,
	colReorder: true, // enable reorder columns
	buttons: [
	            {extend: "copy",
	            	exportOptions: {
	                    columns: [ 0, ":visible" ]
	            	}
	            },
	            {extend: "csv",
	            	exportOptions: {
	                    columns: [ 0, ":visible" ]
	            	}	
	            },
	            {extend: "excel",
	            	exportOptions: {
	                    columns: [ 0, ":visible" ]
	            	}	
	            },
	            {extend: "colvis",
	            	align: "right"
	            }
	        ],
    // always use first column for initial ordering to actually get data displayed
    order: [[ 0, "desc" ]], 
    });
	
	return table;
}

function addSearch(table) {
	// Apply the search to each column footer
	table.columns().every(function() {
		var that = this;

		$("input", this.footer() ).on("keyup change", function() {
			if ( that.search() !== this.value ) {
				that
					.column( $(this).parent().index()+":visible" )
					.search( this.value )
					.draw();
			}
		});
	});
}

function renderDataTable( data ) {
	var tableHeaders = "";
	$.each(data.columns, function(i, val){
        tableHeaders += "<td>" + val + "</td>";
    });

	$("#result-container").empty();
    $("#result-container").append('<table id="result_table" class="display compact" width="100%"><thead><tr>' + tableHeaders + '</tr></thead></table>');
    
    var $table = $( "#result_table" );
    makeFooter($table, tableHeaders);
    var table = initTable($table, data.tableData);
    addSearch(table);
}

function getTableData() {
	$.ajax({
		url: "get_table_data/",
		method: "GET",
		success: function( response ) {
			renderDataTable( response.data );
		},
		complete: function() {
			// Hide the loading message.
			$( "#result--loading" ).hide();
		},
	});
}

function calcFoldChange() {
	
	$.ajax({
		url: "calculate_fold_change/",
		method: "POST",
		data: $( "#fold-change-form" ).serialize(),
		beforeSend: function() {
			// Remove any warnings.
			$( "#fold-change--warning" ).empty();
			// Show loading message.
			var $foldChangeLoading = $( "#fold-change--loading" );
			$foldChangeLoading.removeClass( "invisible" );
			$foldChangeLoading.show();
		},
		success: function( response ) {
			console.log( "fold change response" );
			if ( response.status ) {
				// Response was ok, add fold change to data table.
				dataTable = renderDataTable( response.data ); // Render the new table as DataTable.
			} else {
				// Though the request succeeded, no plot could be generated.
				// Show the error message.
				$( "#fold-change--warning" ).text( response.err_msg );
			}
			
		},
		error: function( xhr, errmsg, err ) {
			// The request did not succeed.
			// Show the HTTP response text as error message.
			console.log( "error while calculating fold change" );
			$( "#fold-change--warning" ).text( xhr.responseText );
		},
		complete: function() {
			// Hide loading messsage.
			$( "#fold-change--loading" ).hide();
		},
	});

}

//Store some fixed elemts.
var $foldChangeBtn = $( "#fold-change--confirm" );
var $resultTableContainer = $( "#result-container" );
var $resultTable = $( "#result_table" );
var dataTable = getTableData();


// Toggle visibility of the experiment parameter table.
$( "#experiment_toggler" ).on( "click", function() {
	if ( $( this ).text() === "Hide experiments" ) {
		$( this ).text('Show experiments');
	} else {
		$( this ).text( "Hide experiments" );
	}
	$( "#view_exps" ).slideToggle( "fast" );
});
// Calculate the fold change when button is clicked.
$foldChangeBtn.on( "click", function() {
	calcFoldChange(dataTable, $resultTableContainer);
});
// Show compare plot when button is clicked.
$( "#plot-compare--confirm" ).on( "click", function () {
	embedSVG( {url: "get_compare_plot/",
		 data: $( "#plot-compare--form" ).serialize(),
		 containerId: "#plot-compare"} 
		 );
});
		




