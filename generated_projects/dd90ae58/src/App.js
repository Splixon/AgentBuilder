import React, { Component } from 'react';
import Forecast from './Forecast';
import WeatherAlerts from './WeatherAlerts';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      userLocation: ''
    };
  }

  componentDidMount() {
    navigator.geolocation.getCurrentPosition(position => {
      this.setState({ userLocation: position.coords.latitude + ', ' + position.coords.longitude });
    });
  }

  render() {
    return (
      <div>
        <h1>Weather App</h1>
        <p>User Location: {this.state.userLocation}</p>
        <Forecast />
        <WeatherAlerts />
      </div>
    );
  }
}

export default App;
