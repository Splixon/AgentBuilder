import React from 'react';
import WeatherCard from './WeatherCard';
import ForecastCard from './ForecastCard';
import './App.css';

class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      location: ''
    };
  }

  componentDidMount() {
    navigator.geolocation.getCurrentPosition(position => {
      this.setState({
        location: {
          lat: position.coords.latitude,
          lon: position.coords.longitude
        }
      });
    });
  }

  render() {
    return (
      <div className="App">
        <header className="App-header">
          <WeatherCard location={this.state.location} />
          <ForecastCard location={this.state.location} />
        </header>
      </div>
    );
  }
}

export default App;
