const chalk = require('chalk');
const fs = require('fs');
const path = require('path');

const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel = process.env.LOG_LEVEL || 'info';
const logFilePath = path.join(__dirname, '..', 'app.log');
const maxLogSize = 1024 * 1024 * 5; // 5MB

function rotateLogFile() {
    try {
        if (fs.existsSync(logFilePath) && fs.statSync(logFilePath).size > maxLogSize) {
            fs.renameSync(logFilePath, `${logFilePath}.old`);
        }
    } catch (err) {
        console.error(chalk.red(`[ERROR] ${new Date().toISOString()}: Could not rotate log file:`), err);
    }
}

function writeToFile(level, message, ...args) {
    const formattedMessage = `[${level.toUpperCase()}] ${new Date().toISOString()}: ${message} ${args.join(' ')}\n`;
    try {
        fs.appendFileSync(logFilePath, formattedMessage);
    } catch (err) {
        console.error(chalk.red(`[ERROR] ${new Date().toISOString()}: Could not write to log file:`), err);
    }
}

const log = {
  level: currentLevel,
  levels: LOG_LEVELS,

  debug: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.debug) {
      console.log(chalk.gray(`[DEBUG] ${new Date().toISOString()}:`), message, ...args);
      writeToFile('debug', message, ...args);
    }
  },
  info: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.info) {
      console.log(chalk.blue(`[INFO] ${new Date().toISOString()}:`), message, ...args);
      writeToFile('info', message, ...args);
    }
  },
  warn: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.warn) {
      console.warn(chalk.yellow(`[WARN] ${new Date().toISOString()}:`), message, ...args);
      writeToFile('warn', message, ...args);
    }
  },
  error: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.error) {
      console.error(chalk.red(`[ERROR] ${new Date().toISOString()}:`), message, ...args);
      writeToFile('error', message, ...args);
    }
  },
  child: function(bindings) {
    const childModule = bindings.module || 'child';
    return {
      debug: (message, ...args) => this.debug(`[${childModule}] ${message}`, ...args),
      info: (message, ...args) => this.info(`[${childModule}] ${message}`, ...args),
      warn: (message, ...args) => this.warn(`[${childModule}] ${message}`, ...args),
      error: (message, ...args) => this.error(`[${childModule}] ${message}`, ...args),
    };
  }
};

rotateLogFile();

module.exports = log;