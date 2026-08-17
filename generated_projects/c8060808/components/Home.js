import React, { Component } from 'react';
import axios from 'axios';
import Note from './Note';
import notes from '../api/notes';

class Home extends Component {
  constructor(props) {
    super(props);
    this.state = {
      notes: []
    };
  }

  componentDidMount() {
    this.fetchNotes();
  }

  fetchNotes = () => {
    notes.getAllNotes()
      .then(response => {
        this.setState({ notes: response.data });
      })
      .catch(error => {
        console.error(error);
      });
  }

  render() {
    return (
      <div>
        <h1>Notes</h1>
        <ul>
          {this.state.notes.map(note => (
            <li key={note.id}>
              <Note note={note} />
            </li>
          ))}
        </ul>
      </div>
    );
  }
}

export default Home;
