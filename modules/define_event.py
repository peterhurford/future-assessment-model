import random
import time

from copy import deepcopy

extinctions = ['xrisk_full_unaligned_tai_extinction', 'xrisk_tai_misuse_extinction',
               'xrisk_nukes_war', 'xrisk_nukes_accident', 'xrisk_unknown_unknown',
               'xrisk_nanotech', 'xrisk_bio_accident', 'xrisk_bio_war', 'xrisk_bio_nonstate',
               'xrisk_supervolcano']

FUTURES = (extinctions + [e + '_but_its_morally_good_actually' for e in extinctions] +
           ['boring', 'xrisk_tai_misuse', 'aligned_tai', 'aligned_tai_ends_time_of_perils',
            'aligned_tai_does_not_end_time_of_perils', 'xrisk_full_unaligned_tai_singleton',
            'xrisk_full_unaligned_but_morally_good_tai_singleton', 'xrisk_subtly_unaligned_tai'])


def define_event(variables, verbosity=0):
    vars_ = deepcopy(variables)
    if verbosity is True:
        verbosity = 1

    if verbosity > 1:
        start1 = time.time()

    state = {'category': 'boring', 'tai': False, 'tai_year': None, 'tai_type': None,
             'tai_alignment_state': None, 'nano': False, 'wars': [], 'war': False,
             'war_start_year': None, 'war_end_year': None, 'russia_nuke_first': False,
             'china_nuke_first': False, 'war_belligerents': None, 'peace_until': None,
             'engineered_pathogen': False, 'natural_pathogen': False, 'lab_leak': False,
             'state_bioweapon': False, 'nonstate_bioweapon': False, 'averted_misalignment': False,
             'nuclear_weapon_used': False, 'catastrophe': [], 'recent_catastrophe_year': None,
             'terminate': False, 'final_year': None, 'double_catastrophe_xrisk': None,
             'initial_delays_calculated': False, 'total_delay': 0, 'compute_needs_announced': False,
             'time_of_perils_end_calculated': False, 'termination_processed': False}
    allowed_state_keys = list(state.keys())
    collectors = {}
    tai_year_data = random.choice(vars_['tai_years'])
    effective_flops = tai_year_data['effective_flop']
    us_china_war_tai_delay_has_occurred = False

    # TODO: Make `vars_['threat_model'] = None` work
    if vars_['threat_model'] is not None:
        for i, v in enumerate(vars_['threat_model']):
            if i == 0:
                vars_['threat_model'][0][1] = float(sq.sample(vars_['threat_model'][0][1]))
            else:
                vars_['threat_model'][i][1] = float(sq.sample(vars_['threat_model'][i][1])) + vars_['threat_model'][i - 1][1]
            # TODO: why is `float` needed here? Produces array(29.15852056) otherwise - should fix.

    vars_['p_narrower_threat_is_xrisk_no_misuse'] = 0.05
    vars_['p_narrower_threat_is_xrisk_misuse'] = 0.7
    vars_['narrower_threat_is_xrisk_no_misuse'] = p_event(vars_, 'p_narrower_threat_is_xrisk_no_misuse', verbosity)
    vars_['narrower_threat_is_xrisk_misuse'] = p_event(vars_, 'p_narrower_threat_is_xrisk_misuse', verbosity)
    
    for y in years:
        vars_['n_catastrophes'] = len(state['catastrophe'])
        vars_['effective_flop'] = effective_flops[y - vars_['CURRENT_YEAR']]

        # Run modules in a random order
        modules = [tai_scenarios_module,
                   great_power_war_scenarios_module,
                   bio_scenarios_module,
                   nuclear_scenarios_module,
                   nano_scenarios_module,
                   supervolcano_scenarios_module,
                   unknown_unknown_scenarios_module]
        random.shuffle(modules)
        for module in modules:
            if state['terminate']:
                if not state['termination_processed']:
                    if state['category'] in extinctions and p_event(vars_, 'extinction_is_morally_good_actually', verbosity):
                        if verbosity:
                            print('...but the extinction is morally good actually because the present/future is net negative')
                        state['category'] = state['category'] + '_but_its_morally_good_actually'
                    elif (state['category'] in ['tai_misuse_extinction', 'xrisk_full_unaligned_tai_singleton'] and 
                          p_event(vars_, 'misaligned_tai_takeover_is_still_morally_fine', verbosity)):
                        state['category'] = 'xrisk_full_unaligned_but_morally_good_tai_singleton'
                        if verbosity:
                            print('...but the TAI singleton is still good because the TAI\'s values are still morally good.')
                    state['termination_processed'] = True
            else:
                state = module(y, state, vars_, verbosity)

        
        # Check for double dip catastrophe
        vars_['catastrophe_this_year'] = len(state['catastrophe']) > vars_['n_catastrophes']
        state = check_for_double_dip_catastrophe(y, state, vars_, verbosity)

        # Modify TAI arrival date for wars and catastrophes
        if not state['terminate'] and state['tai_type'] is None:
            if vars_['catastrophe_this_year']:
                delay = int(np.ceil(sq.sample(vars_['if_catastrophe_delay_tai_arrival_by_years'])))
                state['total_delay'] += delay
                if verbosity > 0:
                    print('...catastrophe delays TAI by {} years (total delay {} years)'.format(delay, state['total_delay']))
            if (state['war'] and
                state['war_start_year'] == y and
                not us_china_war_tai_delay_has_occurred and
                state['war_belligerents'] == 'US/China'):
                us_china_war_tai_delay_has_occurred = True
                delay = int(np.ceil(sq.sample(vars_['if_us_china_war_delay_tai_arrival_by_years'])))
                state['total_delay'] += delay
                if verbosity > 0:
                    print('...US-China war delays TAI by {} years (total delay {} years)'.format(delay, state['total_delay']))
        # TODO: War -> TAI spending increase

        # Check for time of perils
        state = check_for_time_of_perils(y, state, vars_, verbosity)

        # Enforce validity of state
        for k in list(state.keys()):
            if k not in allowed_state_keys:
                raise ValueError('key {} found and not provisioned'.format(k))
        if state['category'] not in FUTURES:
            raise ValueError('State {} not in `FUTURES`'.format(state['category']))

        # Run collectors
        collectors[y] = deepcopy(state)

    if verbosity > 1:
        _mark_time(start1, label='Total loop complete')
            
    # Boring future if MAX_YEAR is reached with no termination
    if not state['terminate']:
        if verbosity > 0:
            if state['category'] == 'aligned_tai_does_not_end_time_of_perils':
                print('...We survive to >{} with aligned TAI but still some perils'.format(y))
            else:
                print('...We survive to >{} with a boring future (no TAI)'.format(y))
        state['final_year'] = '>{}'.format(y)

    if verbosity > 0:
        print('label for this FUTURE => {}'.format(state['category']))
        print('-')
        print('-')
    
    return {'collectors': collectors, 'final_state': state}
