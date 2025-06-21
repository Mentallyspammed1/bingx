// Placeholder for Sex.com custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
class SexComScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    get name() { return 'SexCom'; }
    videoUrl(q,p){ return ''; } async videoParser($d){ return [{title:'SexCom Video Scraper Not Implemented Yet'}];}
    gifUrl(q,p){ return ''; } async gifParser($d){ return [{title:'SexCom GIF Scraper Not Implemented Yet'}];}
}
module.exports = SexComScraper;
