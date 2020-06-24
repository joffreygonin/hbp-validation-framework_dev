import Button from '@material-ui/core/Button';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import Grid from '@material-ui/core/Grid';
import Box from '@material-ui/core/Box';
import axios from 'axios';
import PropTypes from 'prop-types';
import React from 'react';
import ErrorDialog from './ErrorDialog';
import { baseUrl } from "./globals";
import TestInstanceArrayOfForms from './TestInstanceArrayOfForms';
import ContextMain from './ContextMain';
import Theme from './theme';

let versionAxios = null;

export default class TestInstanceAddForm extends React.Component {
    signal = axios.CancelToken.source();
    static contextType = ContextMain;

    constructor(props, context) {
        super(props, context);
        this.handleCancel = this.handleCancel.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleFieldChange = this.handleFieldChange.bind(this);
        this.createPayload = this.createPayload.bind(this);
        this.checkRequirements = this.checkRequirements.bind(this);
        this.checkVersionUnique = this.checkVersionUnique.bind(this);

        const [authContext,] = this.context.auth;
        // console.log(authContext);
        // console.log(authContext.token);

        this.state = {
            instances: [{
                version: "",
                repository: "",
                path: "",
                description: "",
                parameters: ""
            }],
            auth: authContext
        }

        this.handleErrorAddDialogClose = this.handleErrorAddDialogClose.bind(this);
        this.handleCancel = this.handleCancel.bind(this);
        this.checkVersionUnique = this.checkVersionUnique.bind(this);
        this.createPayload = this.createPayload.bind(this);
    }

    handleErrorAddDialogClose() {
        this.setState({ 'errorAddTestInstance': null });
    };

    handleCancel() {
        console.log("Hello")
        this.props.onClose();
    }

    async checkVersionUnique(newVersion) {
        let isUnique = false;
        if (versionAxios) {
            versionAxios.cancel();
        }
        versionAxios = axios.CancelToken.source();

        let url = baseUrl + "/tests/" + this.props.testID + "/instances/?version=" + newVersion;
        let config = {
            cancelToken: versionAxios.token,
            headers: {
                'Authorization': 'Bearer ' + this.state.auth.token,
            }
        };
        await axios.get(url, config)
            .then(res => {
                console.log(res.data.test_codes);
                if (res.data.test_codes.length === 0) {
                    isUnique = true;
                }
            })
            .catch(err => {
                if (axios.isCancel(err)) {
                    console.log('Error: ', err.message);
                } else {
                    console.log(err);
                }
            });
        return isUnique
    }

    createPayload() {
        return [
            {
                test_definition_id: this.props.testID,
                ...this.state.instances[0]
            }
        ]
    }

    async checkRequirements(payload) {
        // rule 1: test instance version cannot be empty
        let error = null;
        if (payload[0].version === "") {
            error = "Test instance 'version' cannot be empty!"
        } else {
            // rule 2: check if version is unique
            let isUnique = await this.checkVersionUnique(payload[0].version);
            if (!isUnique) {
                error = "Test instance 'version' has to be unique within a test!"
            }
        }
        if (error) {
            console.log(error);
            this.setState({
                errorAddTestInstance: error,
            });
            return false;
        } else {
            return true;
        }
    }

    async handleSubmit() {
        let payload = this.createPayload();
        console.log(payload);
        if (await this.checkRequirements(payload)) {
            let url = baseUrl + "/tests/" + this.props.testID + "/instances/";
            let config = {
                cancelToken: this.signal.token,
                headers: {
                    'Authorization': 'Bearer ' + this.state.auth.token,
                    'Content-type': 'application/json'
                }
            };

            axios.post(url, payload, config)
                .then(res => {
                    console.log(res);
                    delete payload[0].test_id
                    this.props.onClose({
                        ...payload[0],
                        id: res.data.uuid[0],
                        uri: "<< missing data >>",
                        timestamp: "<< missing data >>",
                        // TODO: have POST on 'instances' return entire JSON object 
                        // this will provide above missing fields
                    });
                })
                .catch(err => {
                    if (axios.isCancel(err)) {
                        console.log('Error: ', err.message);
                    } else {
                        console.log(err);
                        this.setState({
                            errorAddTestInstance: err,
                        });
                    }
                }
                );
        }
    }

    handleFieldChange(event) {
        const target = event.target;
        let value = target.value;
        const name = target.name;
        console.log(name + " => " + value);
        if (name === "version") {
            this.checkVersionUnique(value)
        }
        this.setState({
            [name]: value
        });
    }

    render() {
        let errorMessage = "";
        if (this.state.errorAddTestInstance) {
            errorMessage = <ErrorDialog open={Boolean(this.state.errorAddTestInstance)} handleErrorDialogClose={this.handleErrorAddDialogClose} error={this.state.errorAddTestInstance.message || this.state.errorAddTestInstance} />
        }
        return (
            <Dialog onClose={this.handleClose}
                aria-labelledby="Form for adding a new test instance"
                open={this.props.open}
                fullWidth={true}
                maxWidth="md">
                <DialogTitle style={{ backgroundColor: Theme.tableHeader }}>Add a new test instance</DialogTitle>
                <DialogContent>
                    <Box my={2}>
                        <form>
                            <Grid container spacing={3}>
                                <TestInstanceArrayOfForms
                                    name="instances"
                                    value={this.state.instances}
                                    onChange={this.handleFieldChange} />
                            </Grid>
                        </form>
                    </Box>
                    <div>
                        {errorMessage}
                    </div>
                </DialogContent>
                <DialogActions>
                    <Button onClick={this.handleCancel} color="default">
                        Cancel
          </Button>
                    <Button onClick={this.handleSubmit} color="primary">
                        Add Test Instance
          </Button>
                </DialogActions>
            </Dialog>
        );
    }
}

TestInstanceAddForm.propTypes = {
    onClose: PropTypes.func.isRequired,
    open: PropTypes.bool.isRequired
};
