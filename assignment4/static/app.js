// Define a global variable to keep track of the current page
var currentPage = 1;

function submitDistanceQuery() {
    var cityName = $('#cityName').val();
    var stateName = $('#stateName').val();

    // AJAX request to get distances
    $.ajax({
        type: 'GET',
        url: '/get_distances',
        data: { cityName: cityName, stateName: stateName,page:currentPage},
        success: function (response) {
            // Update chart and response time
            updateBarChart(response.distances);
            updateResponseTime(response.computationTime);
            console.log(response)

            // Update current page display
            $('#currentPage').text('Page ' + currentPage);
        },
        error: function (error) {
            console.error('Error:', error);
        }
    });
}

function updateBarChart(distances) {
    // var cities = Object.keys(distances);
    // var distancesData = Object.values(distances);
    var cities = distances.map(item => item[0])
    var distancesData = distances.map(item => item[1])


    // Use Chart.js to update the bar chart
    var ctx = document.getElementById('barChart').getContext('2d');
    var barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: cities,
            datasets: [{
                label: 'Distances',
                data: distancesData,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        submitDistanceQuery();
    }
}

function nextPage() {
    currentPage++;
    submitDistanceQuery();
}

function updateResponseTime(responseTime) {
    $('#responseTime').text('Response Time: ' + responseTime + ' ms');
}


$(document).ready(function() {
    $("#avgReviewScoresForm").submit(function(event) {
        event.preventDefault();
        submitForm("/get_average_review_scores", $(this),displayLineChart);
    });

    function submitForm(url, form, callback) {
        $.ajax({
            type: form.attr("method"),
            url: form.attr("action"),
            data: form.serialize(),
            success: function(data) {
                
                callback(data);
            },
            error: function(error) {
                console.error("Error:", error);
            }
        });
    }

    function displayLineChart(data) {
        var cities = data.scores.map(item => item.city_name);
        var avgReviewScores = data.scores.map(item => item.score);

        var ctx = document.getElementById('lineChart').getContext('2d');
        var lineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: cities,
                datasets: [{
                    label: 'Average Review Score',
                    data: avgReviewScores,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1,
                    fill: false
                }]
            },
            options: {
                  scales: {
                            y: {
                             beginAtZero: true
                            }
                  }
            }
        });
    }
});



// $("#avgReviewScoresForm").submit(function(event) {
//     event.preventDefault();
//     submitForm("/get_average_review_scores", $(this), displayLineChart);
// });

// // Function to display the line chart
// function displayLineChart(data) {
//     // Extract data for the line chart
//     var cities = data.distances.map(entry => entry.city);
//     var avgReviewScores = cities.map(city => data.avg_review_scores[city]);

//     // Create a line chart
//     var ctx = document.getElementById('lineChart').getContext('2d');
//     var lineChart = new Chart(ctx, {
//         type: 'line',
//         data: {
//             labels: cities,
//             datasets: [{
//                 label: 'Average Review Score',
//                 data: avgReviewScores,
//                 borderColor: 'rgba(75, 192, 192, 1)',
//                 borderWidth: 1,
//                 fill: false
//             }]
//         }
//     });
// }
