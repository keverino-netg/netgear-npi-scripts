// Zenith ENG Schedule - content from "Zenith ENG Schedule - Bottom Up"
// (rows 7-21, 27-44, 46), with Kevin's approved corrections applied:
//   - Launch / Best Buy / Walmart moved from 3/16/2026 to 3/16/2027 (year typo)
//   - MP Apps approved finish moved from 12/11/2026 to 12/15/2026 (15d from 11/30)
//   - "Intial" -> "Initial" (2 places)
//   - "sprint0" -> "sprint 0"
//   - "stop-ship" -> "stopship" (consistent, no hyphen)
//   - full stop added after "Release Candidates on 11/30"
//   - "next week next Wednesday September 2" -> "next Wednesday September 2"
// Control Run FAI dates left as-is (they account for the holidays).
// Everything else is verbatim; only runs of whitespace are collapsed.

const sq = (s) => s.replace(/\s+/g, ' ').trim();

module.exports = {
  eyebrow: 'ZENITH ENG SCHEDULE',

  slide1: {
    titleThin: 'App-Firmware Integration and ',
    titleBold: 'Dogfooding',
    rows: [
      ['App-FW Integration and Dogfooding', '27d', '8/27/2026', '10/2/2026', true],
      ['SW Integration - sprint 0',         '2d',  '8/27/2026', '8/28/2026', false],
      ['SVT Test - sprint 0',               '5d',  '8/31/2026', '9/4/2026',  false],
      ['SW Integration - sprint 1',         '2d',  '9/3/2026',  '9/4/2026',  false],
      ['SVT Test - sprint 1',               '5d',  '9/7/2026',  '9/11/2026', false],
      ['SW Integration - sprint 2',         '2d',  '9/10/2026', '9/11/2026', false],
      ['SVT Test - sprint 2',               '5d',  '9/14/2026', '9/18/2026', false],
      ['SW Integration - sprint 3',         '2d',  '9/17/2026', '9/18/2026', false],
      ['SVT Test - sprint 3',               '5d',  '9/21/2026', '9/25/2026', false],
      ['SW Integration - sprint 4',         '2d',  '9/24/2026', '9/25/2026', false],
      ['SVT Test - sprint 4',               '5d',  '9/28/2026', '10/2/2026', false],
    ],
    callouts: [
      {
        label: 'App-FW Integration and Dogfooding',
        text: sq('This is a 5-week period where the teams (FW, Apps, and Cloud) coordinate on five week-long sprints that includes both feature finalization and fixing bugs. We will update Dogfooders each week with the coordinated FW and App versions. The end of this process is our final Feature Complete date on 10/02/2026.'),
      },
    ],
  },

  slide2: {
    titleThin: 'End to End Validation and ',
    titleBold: 'External Beta Testing',
    rows: [
      ['End to End Validation',                '10d', '10/5/2026',  '10/16/2026', true],
      ['Beta SW (FW, App, Cloud) SVT Testing', '10d', '10/5/2026',  '10/16/2026', false],
      ['Feature Complete',                     '0d',  '',           '10/16/2026', true],
      ['External Beta Testing',                '20d', '10/19/2026', '11/13/2026', true],
    ],
    callouts: [
      {
        label: 'End to End Validation',
        text: sq('The 10-day End to End Validation period (10/5 to 10/16) focuses fully on finding, testing, and fixing any remaining stopship, since all feature development is done. The emphasis will be on all flows, end to end. We must meet our high quality bar before going to external Beta Testing in the field.'),
      },
      {
        label: 'External Beta Testing',
        text: sq("Beta Start. When we've met our quality bar, we'll start our External Beta Testers on 10/19 to get a much wider range of real-world situation testing across a range of people and environments. This lasts 4 weeks, and the teams will analyze all input and fix all critical bugs or user experiences required, on a controlled basis. Specific testing of Google integrations is in parallel"),
      },
    ],
  },

  // [task, duration, start, finish, bold, description]
  slide3: {
    titleThin: 'MP Firmware and ',
    titleBold: 'Apps',
    // The "Hardware Builds & Go to Market" section header row was dropped -
    // the slide 3 and 4 titles now carry that job.
    rows: [
      ['Beta Bug fixes', '10d', '11/16/2026', '11/27/2026', false,
        sq('Final bugfixing After 4 weeks of Beta testing in the field, we will dedicate 2 weeks to finish fixing all stopship bugs found during Beta.')],
      ['MP FW Candidate Release for SVT', '1d', '11/30/2026', '11/30/2026', false,
        sq('Release Candidates on 11/30. With all bugs fixed we have Release Candidates for both Firmware and Applications.')],
      ['MP SW (FW, App, Cloud) SVT Testing', '5d', '12/1/2026', '12/7/2026', false,
        sq('Post-Release Candidate Final testing on the Release Candidates before releasing to Factory and App Stores')],
      ['MP FW Go-no-go', '1d', '12/8/2026', '12/8/2026', false, ''],
      ['MP Ready Gate Exit (G5)', '1d', '12/9/2026', '12/9/2026', false, ''],
      ['MP Firmware to Factory', '0d', '', '12/9/2026', false, ''],
      ['MP Applications submitted App Stores (iOS and Android)', '0d', '11/30/2026', '11/30/2026', false, ''],
      ['MP Apps approved and appear in App Store', '15d', '', '12/15/2026', false,
        'Standard offsite is 15 days'],
    ],
  },

  slide4: {
    titleThin: 'Factory, Launch, and ',
    titleBold: 'Go to Market',
    rows: [
      ['MP Control Run for New FW', '10d', '12/10/2026', '12/23/2026', false,
        'Initial control run at factory: build 100-200 units'],
      ['Control Run FAI', '3d', '12/24/2026', '1/1/2027', false,
        sq('Our test engineers to validate the whole product based on the initial run at the Factory, leading to FAI')],
      ['MP Build', '17d', '1/4/2027', '1/26/2027', false, 'Start of Mass Production'],
      ['MP XF', '1d', '1/27/2027', '1/27/2027', false, 'Units start to leave Factory'],
      ['DC Arrival', '10d', '1/28/2027', '2/10/2027', false, 'Units start to arrive at DC from Factory'],
      ['DTC "Ready to ship"', '2d', '2/11/2027', '2/12/2027', false, 'Ready to ship from the DC'],
      ['Launch', '1d', '3/16/2027', '3/16/2027', true,
        sq('Marketing launches the product. On-Shelf dates for Best Buy and Walmart and others can follow immediately because the hardware ships earlier than launch')],
      ['Best Buy on shelf', '1d', '3/16/2027', '3/16/2027', false, ''],
      ['Walmart on shelf', '1d', '3/16/2027', '3/16/2027', false, ''],
    ],
    closingNote: sq('Additional milestones for different SKUs, channels, distributions and retail options based on this schedule are in progress by the Zenith Go To Market Team (Sales, Marketing, Operations) and will be published next Wednesday September 2'),
  },
};
