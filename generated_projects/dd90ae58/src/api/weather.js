import axios from 'axios';

const API_KEY = 'YOUR_OPENWEATHERMAP_API_KEY';
const BASE_URL = 'https://api.openweathermap.org/data/2.5';

const getWeatherData = async (location) => {
  try {
    const response = await axios.get(
      `${BASE_URL}/weather?q=${location}&units=metric&appid=${API_KEY}`
    );
    const currentWeather = response.data;

    const forecastResponse = await axios.get(
      `${BASE_URL}/forecast?q=${location}&units=metric&appid=${API_KEY}`
    );
    const forecast = forecastResponse.data;

    return {
      currentWeather,
      forecast,
    };
  } catch (error) {
    console.error(error);
    return null;
  }
};

export { getWeatherData };