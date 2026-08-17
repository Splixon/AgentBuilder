import React from 'react';
import { getWeatherData } from '../weatherAPI';

class WeatherCard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      temperature: '',
      humidity: '',
      conditions: '',
    };
  }

  componentDidMount() {
    getWeatherData().then(data => {
      this.setState({
        temperature: data.temperature,
        humidity: data.humidity,
        conditions: data.conditions,
      });
    });
  }

  render() {
    return (
      <div>
        <h2>Current Weather</h2>
        <p>Temperature: {this.state.temperature}</p>
        <p>Humidity: {this.state.humidity}</p>
        <p>Conditions: {this.state.conditions}</p>
      </div>
    );
  }
}

export default WeatherCard;
