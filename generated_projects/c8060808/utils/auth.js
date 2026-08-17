import axios from 'axios';

const authenticateUser = (username, password) => {
  return new Promise((resolve, reject) => {
    axios.post('/api/authenticate', {
      username,
      password
    })
    .then(response => {
      if (response.data.success) {
        resolve(response.data);
      } else {
        reject(new Error('Authentication failed'));
      }
    })
    .catch(error => {
      reject(error);
    });
  });
};

export { authenticateUser };
