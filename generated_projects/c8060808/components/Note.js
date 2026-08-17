import React from 'react';

class Note {
  constructor(id, title, content) {
    this.id = id;
    this.title = title;
    this.content = content;
  }
}

const NoteComponent = (props) => {
  return (
    <div>
      <h2>{props.note.title}</h2>
      <p>{props.note.content}</p>
    </div>
  );
};

export { Note, NoteComponent };