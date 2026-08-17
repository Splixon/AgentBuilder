import React, { Component } from 'react';
import { getWeatherData } from '../api/weather';

class WeatherAlerts extends Component {
  constructor(props) {
    super(props);
    this.state = {
      weatherAlerts: []
    };
  }

  componentDidMount() {
    getWeatherData().then(data => {
      this.setState({ weatherAlerts: data.weatherAlerts });
    });
  }

  render() {
    return (
      <div>
        <h1>Weather Alerts</h1>
        <ul>
          {this.state.weatherAlerts.map(alert => (
            <li key={alert.id}>{alert.message}</li>
          ))}
        </ul>
      </div>
    );
  }
}

export default WeatherAlerts;
