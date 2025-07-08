const chalk = require('chalk');

const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel = process.env.LOG_LEVEL || 'info';

const log = {
  level: currentLevel,
  levels: LOG_LEVELS,

  debug: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.debug) {
      console.log(chalk.gray(`[DEBUG] ${new Date().toISOString()}:`), message, ...args);
    }
  },
  info: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.info) {
      console.log(chalk.blue(`[INFO] ${new Date().toISOString()}:`), message, ...args);
    }
  },
  warn: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.warn) {
      console.warn(chalk.yellow(`[WARN] ${new Date().toISOString()}:`), message, ...args);
    }
  },
  error: (message, ...args) => {
    if (log.levels[log.level] <= log.levels.error) {
      console.error(chalk.red(`[ERROR] ${new Date().toISOString()}:`), message, ...args);
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

module.exports = log;
