<template>

  <immersive-full-screen
    :backPageText="$tr('selectContent')"
    :backPageLink="goBackLink"
  >
    <subpage-container withSideMargin>
      <task-progress
        v-if="showUpdateProgressBar"
        type="UPDATING_CHANNEL"
        status="QUEUED"
        :percentage="0"
        :showButtons="true"
        :cancellable="true"
        @cleartask="returnToChannelsList"
        id="updatingchannel"
      />
      <task-progress
        v-else-if="taskInProgress"
        type="DOWNLOADING_CHANNEL_CONTENTS"
        v-bind="firstTask"
        :showButtons="true"
        :cancellable="true"
        @cleartask="returnToChannelsList"
      />

      <section class="notifications">
        <ui-alert
          v-if="newVersionAvailable"
          type="info"
          :removeIcon="true"
          :dismissible="false"
        >
          {{ $tr('newVersionAvailableNotification') }}
        </ui-alert>
      </section>

      <section v-if="onDeviceInfoIsReady" class="updates">
        <div
          class="updates-available"
          v-if="newVersionAvailable"
        >
          <span>
            {{ $tr('newVersionAvailable', { version: channel.version }) }}
          </span>
          <k-button
            :text="$tr('update')"
            :primary="true"
            name="update"
            @click="updateChannelMetadata()"
          />
        </div>
        <span v-else>{{ $tr('channelUpToDate') }}</span>
      </section>

      <channel-contents-summary
        :channel="channel"
        :channelOnDevice="channelOnDevice"
      />

      <!-- Assuming that if wizardState.status is truthy, it's an error -->
      <ui-alert
        v-if="wizardStatus!==''"
        type="error"
        :dismissible="false"
      >
        {{ $tr('problemFetchingChannel') }}
      </ui-alert>

      <template v-if="onDeviceInfoIsReady">
        <ui-alert
          v-if="contentTransferError"
          type="error"
          :dismissible="false"
        >
          {{ $tr('problemTransferringContents') }}
        </ui-alert>
        <!-- Contains size estimates + submit button -->
        <selected-resources-size
          :mode="mode"
          :fileSize="nodeCounts.fileSize"
          :resourceCount="nodeCounts.resources"
          :spaceOnDrive="availableSpace"
          @clickconfirm="startTransferringContent()"
        />
        <hr>
        <content-tree-viewer />
      </template>
    </subpage-container>
  </immersive-full-screen>

</template>


<script>

  import kButton from 'kolibri.coreVue.components.kButton';
  import immersiveFullScreen from 'kolibri.coreVue.components.immersiveFullScreen';
  import uiAlert from 'keen-ui/src/UiAlert';
  import isEmpty from 'lodash/isEmpty';
  import subpageContainer from '../containers/subpage-container';
  import { channelIsInstalled, wizardState, nodeTransferCounts } from '../../state/getters';
  import {
    getAvailableSpaceOnDrive,
    updateTreeViewTopic,
  } from '../../state/actions/selectContentActions';
  import {
    downloadChannelMetadata,
    transferChannelContent,
    waitForTaskToComplete,
  } from '../../state/actions/contentTransferActions';
  import { transitionWizardPage, BACKWARD } from '../../state/actions/contentWizardActions';
  import taskProgress from '../manage-content-page/task-progress';
  import { WizardTransitions } from '../../wizardTransitionRoutes';
  import { PageNames, TaskStatuses } from '../../constants';
  import channelContentsSummary from './channel-contents-summary';
  import contentTreeViewer from './content-tree-viewer';
  import selectedResourcesSize from './selected-resources-size';

  export default {
    name: 'selectContentPage',
    components: {
      channelContentsSummary,
      contentTreeViewer,
      immersiveFullScreen,
      kButton,
      selectedResourcesSize,
      subpageContainer,
      taskProgress,
      uiAlert,
    },
    data() {
      return {
        showUpdateProgressBar: false,
        contentTransferError: false,
      };
    },
    computed: {
      channelOnDevice() {
        const installedChannel = this.channelIsInstalled(this.channel.id);
        return (
          installedChannel || {
            on_device_file_size: 0,
            on_device_resources: 0,
          }
        );
      },
      newVersionAvailable() {
        if (this.channelOnDevice.version) {
          return this.channel.version > this.channelOnDevice.version;
        }
        return false;
      },
      goBackLink() {
        return {
          name: WizardTransitions.GOTO_AVAILABLE_CHANNELS_PAGE,
        };
      },
      taskInProgress() {
        return this.firstTask && this.firstTask.status !== TaskStatuses.COMPLETED;
      },
      nodeCounts() {
        return this.nodeTransferCounts(this.transferType);
      },
    },
    mounted() {
      this.getAvailableSpaceOnDrive();
    },
    methods: {
      updateChannelMetadata() {
        // NOTE: This only updates the metadata, not the underlying content.
        // This could produced unexpected behavior for users.
        this.showUpdateProgressBar = true;
        return this.downloadChannelMetadata().then(() => {
          this.showUpdateProgressBar = false;
          // Update the topic in case content names have changed
          this.updateTreeViewTopic(this.topicNode);
          // Update total Channel resource counts
          this.updateResourceCounts();
        });
      },
      startTransferringContent() {
        this.contentTransferError = false;
        return this.transferChannelContent()
          .then(() => {
            this.$router.replace({ name: PageNames.MANAGE_CONTENT_PAGE });
          })
          .catch(() => {
            this.contentTransferError = true;
          });
      },
      returnToChannelsList() {
        this.transitionWizardPage(BACKWARD);
      },
    },
    vuex: {
      getters: {
        availableSpace: state => wizardState(state).availableSpace || 0,
        channel: state => wizardState(state).transferredChannel,
        channelIsInstalled,
        databaseIsLoading: ({ pageState }) => pageState.databaseIsLoading,
        firstTask: ({ pageState }) => pageState.taskList[0],
        mode: state => (wizardState(state).transferType === 'localexport' ? 'export' : 'import'),
        nodeTransferCounts,
        onDeviceInfoIsReady: state => !isEmpty(wizardState(state).currentTopicNode),
        selectedItems: state => wizardState(state).nodesForTransfer || {},
        transferType: state => wizardState(state).transferType,
        wizardStatus: state => wizardState(state).status,
        topicNode: state => wizardState(state).currentTopicNode,
      },
      actions: {
        downloadChannelMetadata,
        getAvailableSpaceOnDrive,
        transferChannelContent,
        waitForTaskToComplete,
        updateTreeViewTopic,
        transitionWizardPage,
        updateResourceCounts(store) {
          const { transferredChannel, availableChannels } = wizardState(store.state);
          const updatedChannel = availableChannels.find(
            channel => channel.id === transferredChannel.id
          );
          store.dispatch('SET_TRANSFERRED_CHANNEL', updatedChannel);
        },
      },
    },
    $trs: {
      channelUpToDate: 'Channel up-to-date',
      newVersionAvailable: 'Version {version, number} available',
      newVersionAvailableNotification:
        'New channel version available. Some of your files may be outdated or deleted.',
      problemFetchingChannel: 'There was a problem getting the contents of this channel',
      problemTransferringContents: 'There was a problem transferring the selected contents',
      selectContent: 'Select content',
      update: 'Update',
    },
  };

</script>


<style lang="stylus" scoped>

  .updates
    text-align: right

</style>
