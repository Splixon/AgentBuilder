import React from 'react';
import { getWeatherData } from '../weatherAPI';

class ForecastCard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      forecastData: [],
    };
  }

  componentDidMount() {
    getWeatherData().then(data => {
      this.setState({ forecastData: data });
    });
  }

  render() {
    return (
      <div>
        {this.state.forecastData.map((day, index) => (
          <div key={index}>
            <h2>{day.date}</h2>
            <p>Temperature: {day.temperature}</p>
            <p>Weather Conditions: {day.weatherConditions}</p>
          </div>
        ))}
      </div>
    );
  }
}

export default ForecastCard;
