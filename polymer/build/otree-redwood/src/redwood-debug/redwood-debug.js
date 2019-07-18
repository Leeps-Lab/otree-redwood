import { html, PolymerElement } from "../../node_modules/@polymer/polymer/polymer-element.js";
import "../../node_modules/@polymer/iron-flex-layout/iron-flex-layout-classes.js";
import '../redwood-events/redwood-events.js';
/*

`<redwood-debug>` is a utility for testing - it can fetch Events from previous
sessions from the oTree server and replay these events back to the
`<redwood-events>` component.

https://otree-redwood.readthedocs.io/webcomponents.html

*/

class RedwoodDebug extends PolymerElement {
  static get properties() {
    return {
      eventsByAppNameThenGroup: {
        type: Object
      },
      apps: {
        type: Array,
        value: () => {
          return [];
        }
      },
      groups: {
        type: Array,
        value: () => {
          return [];
        }
      },
      session: {
        type: String
      },
      app: {
        type: String
      },
      group: {
        type: String
      },
      events: {
        type: Array,
        value: () => {
          return [];
        },
        computed: '_computeEvents(eventsByAppNameThenGroup, app, group)'
      },
      loading: {
        type: Boolean,
        value: false
      },
      playing: {
        type: Boolean,
        value: false
      },
      paused: {
        type: Boolean,
        value: false
      },
      elapsedTime: {
        type: Number,
        value: 0
      }
    };
  }

  static get template() {
    return html`
            <style>
                :host {
                    display: flex;
                    flex-direction: column;
                }
                #chart {
                    min-height: 400px;
                }
            </style>
            <style include="iron-flex iron-flex-alignment"></style>
            <div class="layout horizontal">
                <input
                    type="text"
                    value="{{ session::change }}"
                    placeholder="Session Code"
                    disabled$="[[ loading ]]">
                <button on-tap="_loadSessionEvents">Load</button>
                <select name="appName" value="{{ app::change }}">
                    <template is="dom-repeat" items="[[apps]]">
                        <option value="[[item]]">[[item]]</option>
                    </template>
                </select>
                <select name="groups" value="{{ group::change }}">
                    <template is="dom-repeat" items="[[groups]]">
                        <option value="[[item]]">[[item]]</option>
                    </template>
                </select>
            </div>
            <div class="layout horizontal">
                <button on-tap="_play" hidden$="[[ _hidePlayButton(playing, paused, events.*) ]]">Play</button>
                <button on-tap="_pause" hidden$="[[ _hidePauseButton(playing, paused) ]]">Pause</button>
                <button on-tap="_step" hidden$="[[ _hideStepButton(events.*) ]]">Step</button>
                <button on-tap="_stop" hidden$="[[ _hideStopButton(playing, paused) ]]">Stop</button>
                <span>Elapsed: [[ _displayElapsedTime(elapsedTime) ]]</span>
            </div>
            <div id="chart"></div>
        `;
  }

  connectedCallback() {
    super.connectedCallback();
    this.chart = Highcharts.chart({
      chart: {
        animation: true,
        renderTo: this.$.chart,
        width: this.offsetWidth,
        height: this.offsetHeight
      },
      title: {
        text: null
      },
      exporting: {
        enabled: true
      },
      tooltip: {
        enabled: true
      },
      legend: {
        enabled: true
      },
      credits: {
        enabled: false
      },
      xAxis: {
        type: 'datetime',
        dateTimeLabelFormats: {
          second: '%H:%M:%S'
        },
        plotBands: [{
          value: 0,
          width: 1,
          color: 'green',
          label: {
            text: '',
            layout: 'vertical'
          }
        }]
      },
      yAxis: {
        title: {
          text: ''
        }
      },
      plotOptions: {
        series: {
          states: {
            hover: {
              enabled: true
            }
          }
        }
      },
      line: {
        marker: {
          enabled: false,
          states: {
            hover: {
              enabled: false
            },
            select: {
              enabled: false
            }
          }
        }
      },
      series: [{
        name: 'Events Per Second',
        type: 'area',
        data: []
      }]
    });
    this.currTimeBand = this.chart.xAxis[0].plotLinesAndBands[0];
    this.currEventIndex = 0;
    this.session = window.localStorage.getItem('redwood-debug:session');

    if (this.session) {
      this._loadSessionEvents();
    }
  }

  _loadSessionEvents() {
    if (this.session) {
      window.localStorage.setItem('redwood-debug:session', this.session);
      this.loading = true;
      $.getJSON('/redwood/api/events/session/' + this.session + '/').done(this._initEvents.bind(this)).always(() => {
        this.loading = false;
      });
    }
  }

  _initEvents(eventsByAppNameThenGroup) {
    this.apps = [];
    this.groups = [];

    for (const appName in eventsByAppNameThenGroup) {
      this.push('apps', appName);

      for (const group in eventsByAppNameThenGroup[appName]) {
        this.push('groups', group);
      }
    }

    this.eventsByAppNameThenGroup = eventsByAppNameThenGroup;
    this.app = this.apps[0];
    this.group = this.groups[0];
    let participants = {};

    for (let event of eventsByAppNameThenGroup[this.app][this.group]) {
      if (event.participant) {
        oTree.participantCode = event.participant;
        break;
      }
    }

    oTree.session = this.session;
    oTree.appName = this.app;
    oTree.group = parseInt(this.group);
    window.requestAnimationFrame(this._redrawChart.bind(this));
  }

  _computeEvents(eventsByAppNameThenGroup, app, group) {
    window.requestAnimationFrame(this._redrawChart.bind(this));
    return eventsByAppNameThenGroup[app][group];
  }

  _redrawChart() {
    let bucketStartTime = this.events.length ? this.events[0].timestamp : Date.now();
    const bucketSize = 1000; // 1 seconds, in millis

    const buckets = [];
    buckets.push([bucketStartTime, 0]);

    for (let i = 0; i < this.events.length; i++) {
      const e = this.events[i];

      if (e.channel == 'state') {
        this.chart.xAxis[0].addPlotBand({
          value: e.timestamp,
          width: 1,
          color: 'blue',
          label: {
            text: e.value,
            layout: 'vertical'
          }
        });
      }

      while (e.timestamp - bucketStartTime > bucketSize) {
        bucketStartTime += bucketSize;
        buckets.push([bucketStartTime, 0]);
      }

      buckets[buckets.length - 1][1] += 1;
    } // Remove the last bucket because it still might be collecting events.


    buckets.splice(buckets.length - 1, 1);
    this.chart.series[0].setData(buckets);
  }

  _scheduleReplay() {
    if (!this.playing) {
      return;
    }

    if (this.paused) {
      window.setTimeout(this._scheduleReplay.bind(this), 10);
      return;
    }

    const currEvent = this.events[this.currEventIndex];

    this._replayNextEvent();

    const nextEvent = this.events[this.currEventIndex];
    const delta = nextEvent.timestamp - currEvent.timestamp;
    window.setTimeout(this._scheduleReplay.bind(this), delta);
  }

  _replayNextEvent() {
    const currEvent = this.events[this.currEventIndex];
    console.log(currEvent);
    socket.onmessage({
      data: JSON.stringify({
        channel: currEvent.channel,
        payload: currEvent.value
      })
    });
    this.currTimeBand.options.value = currEvent.timestamp;
    this.currTimeBand.render();
    this.elapsedTime = currEvent.timestamp - this.events[0].timestamp;

    if (this.currEventIndex + 1 >= this.events.length) {
      this._stop();

      return;
    }

    this.currEventIndex += 1;
  }

  _displayElapsedTime(elapsedTime) {
    return (elapsedTime / 1000).toFixed(1);
  }

  _hidePlayButton(playing, paused) {
    return this.events.length == 0 || playing && !paused;
  }

  _hideStepButton() {
    return this.events.length == 0;
  }

  _hidePauseButton(playing, paused) {
    return !playing || paused;
  }

  _hideStopButton(playing, paused) {
    return !playing;
  }

  _play() {
    if (!this.playing) {
      this.playing = true;
      this.elapsedTime = 0;
      this.currEventIndex = 0;

      this._scheduleReplay();
    }

    this.paused = false;
  }

  _pause() {
    this.paused = true;
  }

  _step() {
    this._replayNextEvent();
  }

  _stop() {
    this.elapsedTime = 0;
    this.currTimeBand.destroy();
    this.playing = false;
    this.paused = false;
  }

}

window.customElements.define('redwood-debug', RedwoodDebug);