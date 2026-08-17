// Helper functions for the project
// Import eslint to use its functionality
const eslint = require('eslint');

// Function to run eslint
function runEslint() {
    // Run eslint command
    const cmd = 'eslint .';
    const childProcess = require('child_process);
    childProcess.execSync(cmd);
}

// Call the function to run eslint
runEslint();
