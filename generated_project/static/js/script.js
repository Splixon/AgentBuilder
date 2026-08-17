import React from 'react';
import ReactDOM from 'react-dom';

// Define the WeatherChart component
class WeatherChart extends React.Component {
    render() {
        return (
            <div>
                <h2>Weather Chart</h2>
                <canvas id="weather-chart" width="400" height="200"></canvas>
            </div>
        );
    }
}

// Define the ForecastUpdate component
class ForecastUpdate extends React.Component {
    render() {
        return (
            <div>
                <h2>Forecast Update</h2>
                <p id="forecast-update">Forecast update will be displayed here</p>
            </div>
        );
    }
}

// Render the components to the DOM
ReactDOM.render(<WeatherChart />, document.getElementById('visualization-container'));
ReactDOM.render(<ForecastUpdate />, document.getElementById('visualization-container'));
