<template>

  <div>

    <!-- TODO: RTL - Remove ta-l -->
    <page-header :title="content.title" dir="auto" class="ta-l" />
    <coach-content-label
      class="coach-content-label"
      :value="content.coach_content ? 1 : 0"
      :isTopic="isTopic"
    />

    <content-renderer
      v-if="!content.assessment"
      class="content-renderer"
      @sessionInitialized="setWasIncomplete"
      @startTracking="startTracking"
      @stopTracking="stopTracking"
      @updateProgress="updateProgress"
      :id="content.id"
      :kind="content.kind"
      :files="content.files"
      :contentId="content.content_id"
      :channelId="channelId"
      :available="content.available"
      :extraFields="content.extra_fields"
      :initSession="initSession"
    />

    <assessment-wrapper
      v-else
      class="content-renderer"
      @sessionInitialized="setWasIncomplete"
      @startTracking="startTracking"
      @stopTracking="stopTracking"
      @updateProgress="updateProgress"
      :id="content.id"
      :kind="content.kind"
      :files="content.files"
      :contentId="content.content_id"
      :channelId="channelId"
      :available="content.available"
      :extraFields="content.extra_fields"
      :checkButtonIsPrimary="!showNextBtn"
      :initSession="initSession"
    />

    <k-button
      :primary="true"
      @click="nextContentClicked"
      v-if="showNextBtn"
      class="float"
      :text="$tr('nextContent')"
      alignment="right"
    />

    <!-- TODO consolidate this metadata table with coach/lessons -->
    <!-- TODO: RTL - Remove ta-l -->
    <p v-html="description" dir="auto" class="ta-l"></p>


    <section class="metadata" v-if="showMetadata">
      <!-- TODO: RTL - Do not interpolate strings -->
      <p v-if="content.author">
        {{ $tr('author', {author: content.author}) }}
      </p>

      <p v-if="content.license_name">
        {{ $tr('license', {license: content.license_name}) }}

        <template v-if="content.license_description">
          <ui-icon-button
            :icon="licenceDescriptionIsVisible ? 'expand_less' : 'expand_more'"
            :ariaLabel="$tr('toggleLicenseDescription')"
            size="small"
            type="secondary"
            @click="licenceDescriptionIsVisible = !licenceDescriptionIsVisible"
          />
          <p v-if="licenceDescriptionIsVisible" dir="auto" class="ta-l">
            {{ content.license_description }}
          </p>
        </template>
      </p>

      <p v-if="content.license_owner">
        {{ $tr('copyrightHolder', {copyrightHolder: content.license_owner}) }}
      </p>
    </section>

    <download-button
      v-if="canDownload"
      :files="downloadableFiles"
      class="download-button"
    />

    <slot name="below_content">
      <template v-if="showRecommended">
        <h2>{{ $tr('recommended') }}</h2>
        <content-card-group-carousel
          :genContentLink="genContentLink"
          :header="recommendedText"
          :contents="recommended"
        />
      </template>
    </slot>

    <template v-if="progress >= 1 && wasIncomplete">
      <points-popup
        v-if="showPopup"
        @close="markAsComplete"
        :nextContent="content.next_content"
      >
        <k-button
          v-if="nextContent"
          :primary="true"
          slot="nextItemBtn"
          @click="nextContentClicked"
          :text="$tr('nextContent')"
          alignment="right"
        />
      </points-popup>

      <transition v-else name="slidein" appear>
        <points-slidein @close="markAsComplete" />
      </transition>
    </template>

  </div>

</template>


<script>

  import {
    initContentSession as initSessionAction,
    updateProgress as updateProgressAction,
    startTrackingProgress as startTracking,
    stopTrackingProgress as stopTracking,
  } from 'kolibri.coreVue.vuex.actions';
  import { ContentNodeKinds } from 'kolibri.coreVue.vuex.constants';
  import { isUserLoggedIn, facilityConfig } from 'kolibri.coreVue.vuex.getters';
  import contentRenderer from 'kolibri.coreVue.components.contentRenderer';
  import coachContentLabel from 'kolibri.coreVue.components.coachContentLabel';
  import downloadButton from 'kolibri.coreVue.components.downloadButton';
  import kButton from 'kolibri.coreVue.components.kButton';
  import { isAndroidWebView } from 'kolibri.utils.browser';
  import uiIconButton from 'keen-ui/src/UiIconButton';
  import markdownIt from 'markdown-it';
  import { PageNames, PageModes, ClassesPageNames } from '../constants';
  import { pageMode } from '../state/getters';
  import { updateContentNodeProgress } from '../state/actions/main';
  import pageHeader from './page-header';
  import contentCardGroupCarousel from './content-card-group-carousel';
  import assessmentWrapper from './assessment-wrapper';
  import pointsPopup from './points-popup';
  import pointsSlidein from './points-slidein';
  import { lessonResourceViewerLink } from './classes/classPageLinks';

  export default {
    name: 'contentPage',
    $trs: {
      recommended: 'Recommended',
      nextContent: 'Go to next item',
      author: 'Author: {author}',
      license: 'License: {license}',
      toggleLicenseDescription: 'Toggle license description',
      copyrightHolder: 'Copyright holder: {copyrightHolder}',
    },
    components: {
      coachContentLabel,
      pageHeader,
      contentCardGroupCarousel,
      contentRenderer,
      downloadButton,
      kButton,
      assessmentWrapper,
      pointsPopup,
      pointsSlidein,
      uiIconButton,
    },
    data: () => ({
      wasIncomplete: false,
      licenceDescriptionIsVisible: false,
    }),
    computed: {
      isTopic() {
        return this.content.kind === ContentNodeKinds.TOPIC;
      },
      canDownload() {
        if (this.facilityConfig.showDownloadButtonInLearn && this.content) {
          return (
            this.downloadableFiles.length &&
            this.content.kind !== ContentNodeKinds.EXERCISE &&
            !isAndroidWebView()
          );
        }
        return false;
      },
      description() {
        if (this.content) {
          const md = new markdownIt('zero', { breaks: true });
          return md.render(this.content.description);
        }
      },
      showNextBtn() {
        return this.progress >= 1 && this.content && this.nextContentLink;
      },
      recommendedText() {
        return this.$tr('recommended');
      },
      progress() {
        if (this.isUserLoggedIn) {
          return this.summaryProgress;
        }
        return this.sessionProgress;
      },
      nextContentLink() {
        if (this.content.next_content) {
          // HACK Use a the Resource Viewer Link instead
          if (this.pageName === ClassesPageNames.LESSON_RESOURCE_VIEWER) {
            return lessonResourceViewerLink(Number(this.$route.params.resourceNumber) + 1);
          }
          return this.genContentLink(this.content.next_content.id, this.content.next_content.kind);
        }
        return null;
      },
      showRecommended() {
        if (this.recommended && this.pageMode === PageModes.RECOMMENDED) {
          return true;
        }
        return false;
      },
      showPopup() {
        return (
          this.content.kind === ContentNodeKinds.EXERCISE ||
          this.content.kind === ContentNodeKinds.VIDEO ||
          this.content.kind === ContentNodeKinds.AUDIO
        );
      },
      downloadableFiles() {
        return this.content.files.filter(file => file.preset !== 'Thumbnail');
      },
      showMetadata() {
        // Hide metadata when viewing Resource in a Lesson
        return !this.pageName === ClassesPageNames.LESSON_RESOURCE_VIEWER;
      },
    },
    beforeDestroy() {
      this.stopTracking();
    },
    methods: {
      nextContentClicked() {
        this.$router.push(this.nextContentLink);
      },
      setWasIncomplete() {
        this.wasIncomplete = this.progress < 1;
      },
      initSession() {
        return this.initSessionAction(this.channelId, this.contentId, this.content.kind);
      },
      updateProgress(progressPercent, forceSave = false) {
        const summaryProgress = this.updateProgressAction(progressPercent, forceSave);
        updateContentNodeProgress(this.channelId, this.contentNodeId, summaryProgress);
      },
      markAsComplete() {
        this.wasIncomplete = false;
      },
      genContentLink(id, kind) {
        let name;
        if (kind === ContentNodeKinds.TOPIC) {
          name = PageNames.TOPICS_TOPIC;
        } else {
          name = PageNames.RECOMMENDED_CONTENT;
        }
        return {
          name,
          params: { channel_id: this.channelId, id },
        };
      },
    },
    vuex: {
      getters: {
        content: state => state.pageState.content,
        contentId: state => state.pageState.content.content_id,
        contentNodeId: state => state.pageState.content.id,
        channelId: state => state.pageState.content.channel_id,
        pageName: state => state.pageName,
        recommended: state => state.pageState.recommended,
        summaryProgress: state => state.core.logging.summary.progress,
        sessionProgress: state => state.core.logging.session.progress,
        pageMode,
        isUserLoggedIn,
        facilityConfig,
      },
      actions: {
        initSessionAction,
        updateProgressAction,
        startTracking,
        stopTracking,
      },
    },
  };

</script>


<style lang="stylus" scoped>

  .coach-content-label
    margin: 8px 0

  .content-renderer
    margin-top: 24px

  .float
    float: right

  .metadata
    font-size: smaller

  .download-button
    display: block

  .ta-l
    text-align: left

</style>
