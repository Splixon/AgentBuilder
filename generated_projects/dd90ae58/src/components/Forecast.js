import React, { Component } from 'react';
import { getWeatherData } from '../api/weather';

class Forecast extends Component {
  constructor(props) {
    super(props);
    this.state = {
      weatherData: null
    };
  }

  componentDidMount() {
    getWeatherData().then(data => {
      this.setState({ weatherData: data });
    });
  }

  render() {
    if (!this.state.weatherData) return <div>Loading...</div>;

    const currentWeather = this.state.weatherData.current;
    const fiveDayForecast = this.state.weatherData.fiveDayForecast;

    return (
      <div>
        <h1>Current Weather</h1>
        <p>Temperature: {currentWeather.temp}°C</p>
        <p>Conditions: {currentWeather.conditions}</p>
        <h1>5-Day Forecast</h1>
        {fiveDayForecast.map((day, index) => (
          <div key={index}>
            <p>Day {index + 1}:</p>
            <p>Temperature: {day.temp}°C</p>
            <p>Conditions: {day.conditions}</p>
          </div>
        ))}
      </div>
    );
  }
}

export default Forecast;
