<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <!-- The above 3 meta tags *must* come first in the head; any other head content must come *after* these tags -->

        <title>HeyeHack</title>

        <link href="./bootstrap/css/bootstrap.min.css" rel="stylesheet">
        <link href="./bootstrap/css/ie10-viewport-bug-workaround.css" rel="stylesheet">
        <link href="index.css" rel="stylesheet">

<?php
$user = "USER";
$pass = "PASSWORD";
$dbh = new PDO('mysql:host=localhost;dbname=DATABASE', $user, $pass);
?> 

    </head>

    <body>
        <nav class="navbar navbar-inverse navbar-fixed-top">
            <div class="container">
                <div class="navbar-header">
                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navbar" aria-expanded="false" aria-controls="navbar">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                </div>
                <div id="navbar" class="collapse navbar-collapse">
                    <ul class="nav navbar-nav">
                        <li><a class="navbar-brand" href="http://ds.ds.6cn-prs.6cn.io">Experiment</a></li>
                        <li class="active"><a href="#">Stats</a></li>
                    </ul>
                </div><!--/.nav-collapse -->
            </div>
        </nav>

        <div class="container">

            <div class="title-content">
                <h1>HeyeHack statistics</h1>
            </div>

<?php if (isset($_POST["user_agent"]) && isset($_POST["trace_graph_aaaa"]) && $_POST["trace_graph_aaaa"] == "Yes") echo '<div><canvas id="graph_aaaa" height="80"></canvas></div>'; ?>
<?php if (isset($_POST["user_agent"]) && isset($_POST["trace_graph_synack"]) && $_POST["trace_graph_synack"] == "Yes") echo '<br /><div><canvas id="graph_synack" height="80"></canvas></div>'; ?>

            <br />
            <form action="index.php" method="post">

<?php
foreach($dbh->query('SELECT COUNT(*) as count, user_agent from log group by user_agent ORDER BY count DESC;') as $row) {
    echo '<input type="radio" name="user_agent" value= "'.$row[1].'"> (<b>'.$row[0].'</b>) '.$row[1].'</input><br/>';
}
?>
<br />
<div class="row">
    <div class="col-md-6">
        <input type="checkbox" name="trace_graph_aaaa" value="Yes" checked> Trace AAAA graph
        <ul>
            <li>with SYN-ACK delay over IPv4 between <input type="number" class="param_input" name="synackv4_from" value="0"> and <input type="number" class="param_input" name="synackv4_to" value="0"> ms</li>
            <li>with SYN-ACK delay over IPv6 between <input type="number" class="param_input" name="synackv6_from" value="0"> and <input type="number" class="param_input" name="synackv6_to" value="0"> ms</li>
        </ul>
    </div>
    <div class="col-md-6">
        <input type="checkbox" name="trace_graph_synack" value="Yes" checked> Trace SYN-ACK graph
        <ul>
            <li>with A delay between <input type="number" class="param_input" name="a_from" value="0"> and <input type="number" class="param_input" name="a_to" value="0"> ms</li>
            <li>with AAAA delay between <input type="number" class="param_input" name="aaaa_from" value="0"> and <input type="number" class="param_input" name="aaaa_to" value="0"> ms</li>
        </ul>
    </div>
</div>
With RTT values between <input type="number" class="param_input" name="rtt_from" value="0"> and <input type="number" class="param_input" name="rtt_to" value="200"> ms.
<br /><br />
<input id="trace_button" type="submit" class="btn btn-success btn-lg btn-block" value="Tracer">
            </form>
            <br /><br />
        </div><!-- /.container -->

        <script src="./Chart.js"></script>
<?php
function trace_graph($name_graph, $title, $data_str, $max) {
    echo '
    <script type="text/javascript">
var ctx = document.getElementById("'.$name_graph.'").getContext("2d");
    var labels = [];
    for (var i = 0; i <= 5000; i++) {
        labels.push(i);
    }
    var myChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "'.addslashes($_POST['user_agent']).'", 
                data: '.$data_str.',
                backgroundColor: "rgba(0,0,0,0.9)",
                showLine: false,
                pointRadius: 6,
                /* borderColor: "rgba(0,0,0,0.9)", */
                /* spanGaps: true, */
                /* lineTension: 0, */
                /* fill: false, */
            }]
        },
        options: {
            elements: {
                point: {
                    pointStyle: "rectRounded"
                }
            },
            scales: {
                xAxes : [{
                    id: "xAxe",
                    ticks: {
                        autoSkip: true,
                        autoSkipPadding: 20,
                        min: 0,
                        max: '.$max.',
                    },
                    position: "bottom",
                    scaleLabel: {
                        display: true,
                        labelString: "delay (ms)",
                    },
                }],
                yAxes: [{
                    id: "percentage",
                    type: "linear",
                    position: "left",
                    scaleLabel: {
                        display: true,
                        labelString: "IPv6 percentage",
                    },
                    ticks: {
                        min: 0,
                        max: 100,
                    }
                }]
            },
            title: {
                display: true,
                text: "'.$title.'",
                fontSize: 18
            }
        }
    });
    </script>';
}

if (isset($_POST["user_agent"]) && isset($_POST["trace_graph_aaaa"]) && $_POST["trace_graph_aaaa"] == "Yes") {
    $sql_query = "select delay_aaaa_th, sum(case when ipversion = 'ipv4' then 1 else 0 end) as ipv4_count, sum(case when ipversion = 'ipv6' then 1 else 0 end) as ipv6_count from log where user_agent = :user_agent and :synackv4_from <= delay_synack_v4_th and delay_synack_v4_th <= :synackv4_to and :synackv6_from <= delay_synack_v6_th and delay_synack_v6_th <= :synackv6_to and :rtt_from <= rtt and rtt <= :rtt_to group by delay_aaaa_th order by delay_aaaa_th ASC;";

    if (!(isset($_POST['synackv4_from']) && isset($_POST['synackv4_to']) && isset($_POST['synackv6_from']) && isset($_POST['synackv6_to']) && isset($_POST['rtt_from']) && isset($_POST['rtt_to']))) die("ERROR: param missing");

    $user_agent = $_POST['user_agent'];
    $synackv4_from = $_POST['synackv4_from'];
    $synackv4_to = $_POST['synackv4_to'];
    $synackv6_from = $_POST['synackv6_from'];
    $synackv6_to = $_POST['synackv6_to'];
    $rtt_from = $_POST['rtt_from']*1000;
    $rtt_to = $_POST['rtt_to']*1000;

    $sth = $dbh->prepare($sql_query);
    $sth->bindParam(':user_agent', $user_agent, PDO::PARAM_STR);
    $sth->bindParam(':synackv4_from', $synackv4_from, PDO::PARAM_INT);
    $sth->bindParam(':synackv4_to', $synackv4_to, PDO::PARAM_INT);
    $sth->bindParam(':synackv6_from', $synackv6_from, PDO::PARAM_INT);
    $sth->bindParam(':synackv6_to', $synackv6_to, PDO::PARAM_INT);
    $sth->bindParam(':rtt_from', $rtt_from, PDO::PARAM_INT);
    $sth->bindParam(':rtt_to', $rtt_to, PDO::PARAM_INT);
    $sth->execute();

    $data = array();
    while ($row = $sth->fetch()) {
        $data[$row["delay_aaaa_th"]] = round(100*$row["ipv6_count"]/($row["ipv4_count"]+$row["ipv6_count"]), 3);
    }

    $labels = "[";
    $data_str = "[";
    $max = 0;
    for ($i=0; $i<5000; $i++) {
        if (array_key_exists($i, $data)) {
            $data_str .= $data[$i].",";
            $labels .= $i.",";
            $max = $i;
        } else {
            $data_str .= "null".",";
            $labels .= "null".",";
        }
    }
    $data_str .= "]"; 
    $labels .= "]"; 

    trace_graph("graph_aaaa", "AAAA delay", $data_str, $max);
}

if (isset($_POST["user_agent"]) && isset($_POST["trace_graph_synack"]) && $_POST["trace_graph_synack"] == "Yes") {
    $sql_query = "select delay_synack_v6_th, sum(case when ipversion = 'ipv4' then 1 else 0 end) as ipv4_count, sum(case when ipversion = 'ipv6' then 1 else 0 end) as ipv6_count from log where user_agent = :user_agent and :aaaa_from <= delay_aaaa_th and delay_aaaa_th <= :aaaa_to and :a_from <= delay_a_th and delay_a_th <= :a_to and :rtt_from <= rtt and rtt <= :rtt_to group by delay_synack_v6_th order by delay_synack_v6_th ASC;";

    if (!(isset($_POST['aaaa_from']) && isset($_POST['aaaa_to']) && isset($_POST['a_from']) && isset($_POST['a_to']) && isset($_POST['rtt_from']) && isset($_POST['rtt_to']))) die("ERROR: param missing");

    $user_agent = $_POST['user_agent'];
    $aaaa_from = $_POST['aaaa_from'];
    $aaaa_to = $_POST['aaaa_to'];
    $a_from = $_POST['a_from'];
    $a_to= $_POST['a_to'];
    $rtt_from = $_POST['rtt_from']*1000;
    $rtt_to = $_POST['rtt_to']*1000;

    $sth = $dbh->prepare($sql_query);
    $sth->bindParam(':user_agent', $user_agent, PDO::PARAM_STR);
    $sth->bindParam(':aaaa_from', $aaaa_from, PDO::PARAM_INT);
    $sth->bindParam(':aaaa_to', $aaaa_to, PDO::PARAM_INT);
    $sth->bindParam(':a_from', $a_from, PDO::PARAM_INT);
    $sth->bindParam(':a_to', $a_to, PDO::PARAM_INT);
    $sth->bindParam(':rtt_from', $rtt_from, PDO::PARAM_INT);
    $sth->bindParam(':rtt_to', $rtt_to, PDO::PARAM_INT);
    $sth->execute();

    $data = array();
    while ($row = $sth->fetch()) {
        $data[$row["delay_synack_v6_th"]] = round(100*$row["ipv6_count"]/($row["ipv4_count"]+$row["ipv6_count"]), 3);
    }

    $labels = "[";
    $data_str = "[";
    $max = 0;
    for ($i=0; $i<5000; $i++) {
        if (array_key_exists($i, $data)) {
            $data_str .= $data[$i].",";
            $labels .= $i.",";
            $max = $i;
        } else {
            $data_str .= "null".",";
            $labels .= "null".",";
        }
    }
    $data_str .= "]"; 
    $labels .= "]"; 

    trace_graph("graph_synack", "SYN-ACK delay", $data_str, $max);
}

?>
    <!-- Bootstrap core JavaScript
    ================================================== -->
    <!-- Placed at the end of the document so the pages load faster -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
    <script>window.jQuery || document.write('<script src="./bootstrap/js/vendor/jquery.min.js"><\/script>')</script>
    <script src="./bootstrap/js/bootstrap.min.js"></script>
    </body>

<?php
$dbh = null;
?>
</html>
